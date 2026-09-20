"""Tests for server.poller."""
from __future__ import annotations

import threading

import pytest

from server.devin import Attachment, DevinMessage, DevinUnavailable, FakeDevin, SessionSnapshot
from server.poller import LOST_CONTACT, LOST_CONTACT_AFTER, Poller
from server.store import Store


class ScriptedDevin:
    """Per-session canned answers; a session listed in `down` raises instead."""

    def __init__(self):
        self.snapshots: dict[str, SessionSnapshot] = {}
        self.messages: dict[str, list[DevinMessage]] = {}
        self.attachments: dict[str, list[Attachment]] = {}
        self.down: dict[str, Exception] = {}
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
    assert [e["text"] for e in store.list_events(mission.id)] == ["Late thought"]


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
