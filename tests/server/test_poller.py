"""Tests for server.poller."""
from __future__ import annotations

import io
import threading
import zipfile

import pytest

from server.brief import build_explorer_request
from server.devin import (
    Attachment,
    AttachmentRejected,
    AttachmentUnavailable,
    DevinMessage,
    DevinUnavailable,
    FakeDevin,
    SessionSnapshot,
)
from server.poller import LOST_CONTACT, LOST_CONTACT_AFTER, Poller
from server.store import Store


class ScriptedDevin:
    """Per-session canned answers; a session listed in `down` raises instead."""

    def __init__(self):
        self.snapshots: dict[str, SessionSnapshot] = {}
        self.messages: dict[str, list[DevinMessage]] = {}
        self.attachments: dict[str, list[Attachment]] = {}
        self.down: dict[str, Exception] = {}
        self.files: dict[str, bytes | Exception] = {}
        self.calls: list[tuple[str, str]] = []

    def _answer(self, name, session_id, table, default):
        self.calls.append((name, session_id))
        if session_id in self.down:
            raise self.down[session_id]
        return table.get(session_id, default)

    def get_session(self, session_id):
        return self._answer("get_session", session_id, self.snapshots, SessionSnapshot("running", None, None))

    def list_messages(self, session_id):
        return self._answer("list_messages", session_id, self.messages, [])

    def list_attachments(self, session_id):
        return self._answer("list_attachments", session_id, self.attachments, [])

    def download_file(self, attachment):
        self.calls.append(("download_file", attachment.name))
        result = self.files[attachment.name]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "k.db")


@pytest.fixture
def devin():
    return ScriptedDevin()


def _mission(store, session_id):
    row = store.create_mission("h", title="t", dataset_ids=[], reference=None, prompt="the brief " * 10)
    if session_id:
        store.set_session(row.id, session_id, None)
    return row


def _kinds(store, mission_id):
    return [event["kind"] for event in store.list_events(mission_id)]


def test_tick_syncs_every_live_mission(store, devin):
    a, b = _mission(store, "devin-a"), _mission(store, "devin-b")
    devin.messages["devin-a"] = [DevinMessage("1", "devin", "From A", "")]
    devin.messages["devin-b"] = [DevinMessage("1", "devin", "From B", "")]
    devin.snapshots["devin-b"] = SessionSnapshot("waiting", None, {"needs_user": "Which one?"})

    Poller(store, devin).tick()

    assert [e["text"] for e in store.list_events(a.id)] == ["From A"]
    assert [e["text"] for e in store.list_events(b.id)] == ["From B"]
    assert store.get_mission(a.id).status == "working"
    waiting = store.get_mission(b.id)
    assert (waiting.status, waiting.needs_user) == ("waiting", "Which one?")


def test_tick_skips_done_failed_and_sessionless_missions(store, devin):
    done, failed, sessionless = _mission(store, "devin-done"), _mission(store, "devin-failed"), _mission(store, None)
    store.mark_done(done.id)
    store.fail(failed.id, "boom")
    Poller(store, devin).tick()
    assert devin.calls == []
    assert store.list_events(sessionless.id) == []


def test_waiting_missions_keep_syncing(store, devin):
    mission = _mission(store, "devin-a")
    devin.snapshots["devin-a"] = SessionSnapshot("waiting", None, None)
    poller = Poller(store, devin)
    poller.tick()
    devin.snapshots["devin-a"] = SessionSnapshot("running", None, None)
    poller.tick()
    assert store.get_mission(mission.id).status == "working"


def test_one_failing_mission_does_not_stop_the_others(store, devin):
    broken, crashing, healthy = _mission(store, "devin-x"), _mission(store, "devin-y"), _mission(store, "devin-z")
    devin.down["devin-x"] = DevinUnavailable("503")
    devin.down["devin-y"] = RuntimeError("bug in the client")
    devin.messages["devin-z"] = [DevinMessage("1", "devin", "Still fine", "")]

    Poller(store, devin).tick()

    assert [e["text"] for e in store.list_events(healthy.id)] == ["Still fine"]
    assert store.get_mission(broken.id).status == "working"
    assert store.get_mission(crashing.id).status == "working"
    assert store.list_events(broken.id) == [] and store.list_events(crashing.id) == []


def test_lost_contact_is_reported_once_after_five_failures_and_resets_on_success(store, devin):
    mission = _mission(store, "devin-x")
    devin.down["devin-x"] = DevinUnavailable("503")
    poller = Poller(store, devin)

    for _ in range(LOST_CONTACT_AFTER - 1):
        poller.tick()
    assert store.list_events(mission.id) == []

    for _ in range(4):
        poller.tick()
    events = store.list_events(mission.id)
    assert [(e["kind"], e["text"]) for e in events] == [("error", LOST_CONTACT)]
    assert store.get_mission(mission.id).status == "working"

    del devin.down["devin-x"]
    poller.tick()
    assert store.get_mission(mission.id).failures == 0

    devin.down["devin-x"] = DevinUnavailable("503")
    for _ in range(LOST_CONTACT_AFTER):
        poller.tick()
    assert _kinds(store, mission.id) == ["error", "error"]


def test_attachments_are_only_listed_when_the_output_refers_to_one(store, devin):
    mission = _mission(store, "devin-a")
    poller = Poller(store, devin)
    poller.tick()
    assert ("list_attachments", "devin-a") not in devin.calls

    devin.snapshots["devin-a"] = SessionSnapshot("running", None, {"artifacts": [
        {"id": "a1", "type": "image", "title": "Map", "src": "attachment:map.png"}]})
    devin.attachments["devin-a"] = [Attachment("map.png", "https://files.test/map.png")]
    poller.tick()
    assert ("list_attachments", "devin-a") in devin.calls
    assert store.list_events(mission.id)[-1]["artifact"]["src"].endswith("/attachments/map.png")


def test_session_error_fails_the_mission_and_stops_polling_it(store, devin):
    mission = _mission(store, "devin-a")
    devin.snapshots["devin-a"] = SessionSnapshot("error", "out_of_credits", None)
    poller = Poller(store, devin)
    poller.tick()
    poller.tick()
    assert store.get_mission(mission.id).status == "failed"
    assert _kinds(store, mission.id) == ["error"]
    assert devin.calls.count(("get_session", "devin-a")) == 1


def test_mark_done_during_a_sync_is_not_undone(store, devin):
    mission = _mission(store, "devin-a")

    class MarksDoneMidSync(ScriptedDevin):
        def list_messages(self, session_id):
            store.mark_done(mission.id)
            return [DevinMessage("1", "devin", "Late thought", "")]

    Poller(store, MarksDoneMidSync()).tick()
    assert store.get_mission(mission.id).status == "done"
    assert store.list_events(mission.id) == []  # The entire stale response is discarded.


def test_routine_pause_resumes_once_but_an_explicit_pause_is_respected(store, devin):
    mission = _mission(store, "devin-a")
    store.set_autonomy(mission.id, auto_phase="research")
    sent = []
    devin.send_message = lambda session_id, text: sent.append(text)
    devin.snapshots["devin-a"] = SessionSnapshot("waiting", None, {"needs_user": "Choose a method?"})
    poller = Poller(store, devin)
    poller.tick()
    poller.tick()  # The unchanged waiting snapshot is not another request.
    assert len(sent) == 1
    assert store.get_mission(mission.id).status == "working"
    devin.snapshots["devin-a"] = SessionSnapshot("running", None, {"needs_user": None})
    poller.tick()
    devin.snapshots["devin-a"] = SessionSnapshot("waiting", None, {"run_status": "paused"})
    poller.tick()
    assert store.get_mission(mission.id).status == "waiting"
    assert store.get_mission(mission.id).needs_user == "Paused at your request"
    assert len(sent) == 1


def test_steering_during_a_working_poll_discards_the_previous_response(store):
    mission = _mission(store, "devin-a")

    class SteeredMidSync(ScriptedDevin):
        def list_messages(self, session_id):
            store.reopen(mission.id)
            return [DevinMessage("1", "devin", "Old response", "")]

    devin = SteeredMidSync()
    devin.snapshots["devin-a"] = SessionSnapshot("waiting", None, {"needs_user": "Old question?"})
    Poller(store, devin).tick()
    assert store.get_mission(mission.id).status == "working"
    assert store.list_events(mission.id) == []


def test_resumes_missions_from_disk_after_a_restart(tmp_path, devin):
    path = tmp_path / "k.db"
    mission = _mission(Store(path), "devin-a")
    devin.messages["devin-a"] = [DevinMessage("1", "devin", "Back again", "")]
    restarted = Store(path)
    Poller(restarted, devin).tick()
    assert [e["text"] for e in restarted.list_events(mission.id)] == ["Back again"]


def test_a_full_demo_run_through_the_poller(store):
    clock = [1_800_000_000.0]
    fake = FakeDevin(clock=lambda: clock[0], beat_seconds=3.0)
    mission = _mission(store, fake.create_session("the brief " * 10, title="t", schema={}, max_acu=5).session_id)
    poller = Poller(store, fake)

    counts = []
    for _ in range(12):
        poller.tick()
        counts.append(len(store.list_events(mission.id)))
        clock[0] += 5
    assert counts == sorted(counts) and counts[0] < counts[-1]

    kinds = _kinds(store, mission.id)
    assert kinds.count("step") == 5 and kinds.count("artifact") == 7 and kinds.count("thought") >= 6
    assert kinds[-1] == "conclusion"
    assert store.get_mission(mission.id).status == "waiting"
    assert "the brief" not in " ".join(e.get("text", "") for e in store.list_events(mission.id))

    before = store.list_events(mission.id)
    poller.tick()
    assert store.list_events(mission.id) == before


def test_loop_ticks_until_stopped_and_survives_a_crashing_tick(store, devin, monkeypatch):
    _mission(store, "devin-a")
    live_missions = store.live_missions
    ticks: list[int] = []
    sleeps: list[float] = []

    def flaky_live_missions():
        ticks.append(len(ticks))
        if len(ticks) == 1:
            raise RuntimeError("store exploded")
        return live_missions()

    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 3:
            poller.stop()

    monkeypatch.setattr(store, "live_missions", flaky_live_missions)
    poller = Poller(store, devin, interval=5.0, sleep=sleep)
    poller.run()
    assert ticks == [0, 1, 2] and sleeps == [5.0, 5.0, 5.0]
    assert devin.calls.count(("get_session", "devin-a")) == 2


def test_start_runs_a_daemon_thread_and_stop_ends_it(store, devin):
    mission = _mission(store, "devin-a")
    devin.messages["devin-a"] = [DevinMessage("1", "devin", "Hello", "")]
    synced = threading.Event()

    class Signalling(ScriptedDevin):
        def list_messages(self, session_id):
            synced.set()
            return devin.list_messages(session_id)

    poller = Poller(store, Signalling(), interval=0.01)
    thread = poller.start()
    assert thread.daemon
    assert synced.wait(2)
    poller.stop()
    thread.join(2)
    assert not thread.is_alive()
    assert [e["text"] for e in store.list_events(mission.id)] == ["Hello"]
    assert poller.start() is not thread
    poller.stop()


# ---------- explorer builds ----------

NOW = "2026-09-20T13:00:00Z"
SITE = {"index.html": b"<!doctype html><title>Roofs</title>", "data.json": b'{"rows": [1]}',
        "kit/kit.css": b"from the archive"}


def _zip(files=SITE) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _announce(devin, session_id, version=1, files=SITE, **over):
    """Devin says build `version` is ready and its archive is among the attachments."""
    name = f"explorer-v{version}.zip"
    explorer = {"version": version, "archive": name, "entry": "index.html", "title": "Roofs by score",
                "description": "Click a roof.", **over}
    devin.snapshots[session_id] = SessionSnapshot("waiting", None, {"steps": [], "artifacts": [], "explorer": explorer})
    devin.attachments[session_id] = [Attachment("plot.png", "u"), Attachment(name, "u", f"att-{version}")]
    devin.files[name] = files if isinstance(files, (bytes, Exception)) else _zip(files)


@pytest.fixture
def poller(store, devin):
    return Poller(store, devin)


def _asked(store, session_id):
    mission = _mission(store, session_id)
    store.request_explorer(mission.id)
    return store.get_mission(mission.id)


def _files(store, mission_id, version):
    root = store.explorer_dir(mission_id, version)
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_a_due_build_is_downloaded_unpacked_and_delivered(tmp_path, devin):
    store = Store(tmp_path / "k.db")
    mission = _asked(store, "devin-a")
    _announce(devin, "devin-a")
    Poller(store, devin, now=lambda: NOW).tick()

    row = store.get_mission(mission.id)
    assert row.explorer == {"version": 1, "title": "Roofs by score", "description": "Click a roof.",
                            "entry": "index.html", "builtAt": NOW}
    assert (row.explorer_pending, row.explorer_seen_version, row.status) == (False, 1, "waiting")
    assert _kinds(store, mission.id) == ["explorer"]
    assert store.explorer_dir(mission.id, 1) == tmp_path / "explorers" / mission.id / "1"
    assert _files(store, mission.id, 1) == {"index.html": SITE["index.html"], "data.json": SITE["data.json"]}
    assert devin.calls.count(("download_file", "explorer-v1.zip")) == 1


def test_a_delivered_build_is_not_fetched_again(store, devin, poller):
    mission = _asked(store, "devin-a")
    _announce(devin, "devin-a")
    for _ in range(3):
        poller.tick()
    assert devin.calls.count(("download_file", "explorer-v1.zip")) == 1
    assert _kinds(store, mission.id) == ["explorer"]
    # Nor are the attachments listed once nothing is awaited.
    assert devin.calls.count(("list_attachments", "devin-a")) == 1


def test_nothing_is_fetched_for_a_build_nobody_asked_for(store, devin, poller):
    mission = _mission(store, "devin-a")
    _announce(devin, "devin-a")
    poller.tick()
    assert ("list_attachments", "devin-a") not in devin.calls and ("download_file", "explorer-v1.zip") not in devin.calls
    assert store.get_mission(mission.id).explorer is None


def test_attachments_are_not_listed_until_a_new_build_is_announced(store, devin, poller):
    mission = _asked(store, "devin-a")
    poller.tick()
    assert ("list_attachments", "devin-a") not in devin.calls
    assert store.get_mission(mission.id).explorer_pending


def test_an_announced_build_waits_for_its_archive(store, devin, poller):
    mission = _asked(store, "devin-a")
    _announce(devin, "devin-a")
    devin.attachments["devin-a"] = [Attachment("plot.png", "u")]
    poller.tick()
    row = store.get_mission(mission.id)
    assert (row.explorer, row.explorer_pending, row.status) == (None, True, "working")
    assert ("download_file", "explorer-v1.zip") not in devin.calls

    devin.attachments["devin-a"].append(Attachment("explorer-v1.zip", "u"))
    poller.tick()
    assert store.get_mission(mission.id).explorer["version"] == 1


@pytest.mark.parametrize("files, reason", [
    ({"index.html": b"x", "run.exe": b"MZ"}, "'run.exe' is not an allowed kind of file"),
    ({"index.html": b"x", "../evil.html": b"x"}, "climbs out of the archive"),
    ({"main.html": b"x"}, "its entry page 'index.html' is missing"),
    (b"this is not a zip", "it is not a zip archive"),
    (AttachmentRejected("attachment is larger than 40 MB"), "attachment is larger than 40 MB"),
    (AttachmentRejected("attachment download failed (404)"), "its archive could not be downloaded"),
])
def test_an_unusable_archive_ends_the_request_with_an_error_that_names_the_reason(store, devin, poller, files, reason):
    mission = _asked(store, "devin-a")
    _announce(devin, "devin-a", files=files)
    poller.tick()
    row = store.get_mission(mission.id)
    assert (row.explorer, row.explorer_pending, row.explorer_seen_version, row.status) == (None, False, 1, "waiting")
    (error,) = store.list_events(mission.id)
    assert error["kind"] == "error" and error["text"].startswith("The explorer could not be used: ")
    assert reason in error["text"]
    assert not store.explorer_dir(mission.id, 1).exists()

    # Asking again does not fetch the same bad archive; the next version is what counts.
    store.request_explorer(mission.id)
    poller.tick()
    assert devin.calls.count(("download_file", "explorer-v1.zip")) == 1
    _announce(devin, "devin-a", version=2)
    poller.tick()
    assert store.get_mission(mission.id).explorer["version"] == 2


@pytest.mark.parametrize("failure", [
    AttachmentUnavailable("attachment download failed (503)"), DevinUnavailable("Devin identity lookup failed (503)"),
    OSError("disk full"),
])
def test_a_download_that_may_yet_work_is_tried_again_and_the_rest_of_the_sync_goes_ahead(store, devin, poller, failure):
    mission = _asked(store, "devin-a")
    _announce(devin, "devin-a", files=failure)
    devin.messages["devin-a"] = [DevinMessage("1", "devin", "The explorer is ready.", "")]
    poller.tick()
    row = store.get_mission(mission.id)
    assert (row.explorer, row.explorer_pending, row.status, row.failures) == (None, True, "working", 0)
    assert _kinds(store, mission.id) == ["thought"]

    devin.files["explorer-v1.zip"] = _zip()
    poller.tick()
    assert store.get_mission(mission.id).explorer["version"] == 1
    assert _kinds(store, mission.id) == ["thought", "explorer"]


def test_a_download_that_never_works_is_given_up_on_at_the_deadline(tmp_path, devin):
    store = Store(tmp_path / "k.db", now=lambda: NOW)
    mission = _asked(store, "devin-a")
    _announce(devin, "devin-a", files=AttachmentUnavailable("attachment download failed (503)"))
    Poller(store, devin, now=lambda: "2026-09-20T13:14:59Z").tick()
    assert store.get_mission(mission.id).explorer_pending and store.list_events(mission.id) == []
    Poller(store, devin, now=lambda: "2026-09-20T13:15:01Z").tick()
    row = store.get_mission(mission.id)
    assert (row.explorer, row.explorer_pending, row.explorer_seen_version) == (None, False, 0)
    assert [e["text"] for e in store.list_events(mission.id)] == ["The explorer did not arrive"]


def test_a_failing_explorer_does_not_stop_other_missions(store, devin, poller):
    bad, crashing, good = _asked(store, "devin-x"), _asked(store, "devin-y"), _asked(store, "devin-z")
    _announce(devin, "devin-x", version=1, files={"index.html": b"x", "run.exe": b"MZ"})
    _announce(devin, "devin-y", version=2, files=RuntimeError("bug in the client"))
    _announce(devin, "devin-z", version=3)
    poller.tick()
    assert _kinds(store, bad.id) == ["error"]
    assert store.list_events(crashing.id) == [] and store.get_mission(crashing.id).explorer_pending
    assert store.get_mission(good.id).explorer["version"] == 3


def test_a_change_request_unpacks_next_to_the_old_version(store, devin, poller):
    mission = _asked(store, "devin-a")
    _announce(devin, "devin-a")
    poller.tick()
    store.request_explorer(mission.id)
    poller.tick()
    assert store.get_mission(mission.id).explorer_pending

    _announce(devin, "devin-a", version=2, files={"index.html": b"second"}, title="Roofs with a heatmap")
    poller.tick()
    row = store.get_mission(mission.id)
    assert (row.explorer["version"], row.explorer["title"], row.explorer_pending) == (2, "Roofs with a heatmap", False)
    assert _files(store, mission.id, 1)["index.html"] == SITE["index.html"]
    assert _files(store, mission.id, 2) == {"index.html": b"second"}
    assert _kinds(store, mission.id) == ["explorer"]


def test_a_mission_marked_done_while_its_build_is_pending_still_gets_it(store, devin, poller):
    mission = _asked(store, "devin-a")
    store.mark_done(mission.id)
    _announce(devin, "devin-a")
    poller.tick()
    row = store.get_mission(mission.id)
    assert (row.status, row.explorer["version"], row.explorer_pending) == ("done", 1, False)
    poller.tick()
    assert devin.calls.count(("get_session", "devin-a")) == 1


def test_a_custom_entry_is_what_gets_checked(store, devin, poller):
    mission = _asked(store, "devin-a")
    _announce(devin, "devin-a", files={"pages/start.html": b"x", "data.json": b"{}"}, entry="pages/start.html")
    poller.tick()
    assert store.get_mission(mission.id).explorer["entry"] == "pages/start.html"


def test_a_full_demo_explorer_build_through_the_poller(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    for name, text in {"GUIDE.md": "guide", "kit.css": "body {}", "kit.js": "1", "index.html": "<p>example</p>",
                       "data.json": "{}"}.items():
        (kit / name).write_text(text)
    store = Store(tmp_path / "k.db")
    clock = [1_800_000_000.0]
    fake = FakeDevin(clock=lambda: clock[0], beat_seconds=3.0, kit_dir=kit)
    mission = _mission(store, fake.create_session("the brief " * 10, title="t", schema={}, max_acu=5).session_id)
    poller = Poller(store, fake)
    for _ in range(12):
        poller.tick()
        clock[0] += 5

    fake.send_message(store.get_mission(mission.id).session_id,
                      build_explorer_request(None, {"GUIDE.md": "guide"}, next_version=1))
    store.request_explorer(mission.id)
    for _ in range(3):
        poller.tick()
        clock[0] += 5
    row = store.get_mission(mission.id)
    assert (row.status, row.explorer_pending, row.explorer["version"]) == ("waiting", False, 1)
    assert _kinds(store, mission.id)[-2:] == ["conclusion", "explorer"]
    assert _files(store, mission.id, 1) == {"index.html": b"<p>example</p>", "data.json": b"{}"}
