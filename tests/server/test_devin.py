"""Tests for server.devin: FakeDevin's script and V3DevinClient against stubbed requests."""
from __future__ import annotations

import io
import zipfile

import pytest
import requests

from server import devin
from server.artifacts import normalise_artifact
from server.brief import REPORT_REQUEST, build_explorer_request
from server.devin import (
    Attachment,
    AttachmentRejected,
    AttachmentUnavailable,
    DevinMessage,
    DevinUnavailable,
    FakeDevin,
    SessionRef,
    V3DevinClient,
    make_client,
    max_acu,
)
from server.explorer import unpack
from server.report import normalise_report

KEY = "cog_test_key"
ORG = "org-123"
BASE = f"https://api.devin.ai/v3/organizations/{ORG}"


# ---------- FakeDevin ----------

class Ticker:
    def __init__(self):
        self.t = 1_800_000_000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def ticker():
    return Ticker()


@pytest.fixture
def kit(tmp_path):
    """A stand-in kit: the real one is someone else's to change, so no test here reads its contents."""
    root = tmp_path / "kit"
    root.mkdir()
    for name, text in {"GUIDE.md": "the guide", "kit.css": "body {}", "kit.js": "export {}",
                       "index.html": "<!doctype html><title>example</title>", "data.json": '{"rows": [1]}'}.items():
        (root / name).write_text(text)
    return root


@pytest.fixture
def fake(ticker, kit):
    return FakeDevin(clock=ticker, beat_seconds=3.0, kit_dir=kit)


def _start(fake):
    return fake.create_session("the brief", title="Kingdom: t", schema={}, max_acu=5)


def _devin_texts(fake, session_id):
    return [m.text for m in fake.list_messages(session_id) if m.role == "devin"]


def test_fake_session_ref(fake):
    first, second = _start(fake), _start(fake)
    assert isinstance(first, SessionRef)
    assert first.session_id.startswith("devin-") and first.session_id != second.session_id
    assert first.url is None


def test_fake_starts_running_with_the_prompt_echoed(fake):
    ref = _start(fake)
    snapshot = fake.get_session(ref.session_id)
    assert snapshot.status == "running"
    messages = fake.list_messages(ref.session_id)
    assert messages[0] == DevinMessage(id=messages[0].id, role="user", text="the brief", at=messages[0].at)


def test_fake_progresses_with_the_clock_and_never_goes_backwards(fake, ticker):
    ref = _start(fake)
    seen_messages, seen_steps, seen_artifacts = 0, 0, 0
    for _ in range(40):
        ticker.t += 1.5
        output = fake.get_session(ref.session_id).structured_output
        messages = len(fake.list_messages(ref.session_id))
        assert messages >= seen_messages
        assert len(output["steps"]) >= seen_steps
        assert len(output["artifacts"]) >= seen_artifacts
        seen_messages, seen_steps, seen_artifacts = messages, len(output["steps"]), len(output["artifacts"])
    assert seen_messages > 1


def test_fake_has_at_most_one_active_step_at_any_time(fake, ticker):
    ref = _start(fake)
    for _ in range(40):
        ticker.t += 1.0
        steps = fake.get_session(ref.session_id).structured_output["steps"]
        assert sum(step["state"] == "active" for step in steps) <= 1


def test_fake_full_run_ends_waiting_with_everything(fake, ticker):
    ref = _start(fake)
    ticker.t += 600
    snapshot = fake.get_session(ref.session_id)
    output = snapshot.structured_output
    assert snapshot.status == "waiting"
    assert len(output["steps"]) == 5
    assert all(step["state"] == "done" for step in output["steps"])
    assert {a["type"] for a in output["artifacts"]} == {"chart", "images", "relation", "table", "stats", "image"}
    assert output["conclusion"]["verdict"] and output["conclusion"]["summary"] and output["conclusion"]["stats"]
    assert len(_devin_texts(fake, ref.session_id)) >= 6


def test_fake_artifacts_all_survive_validation(fake, ticker):
    ref = _start(fake)
    ticker.t += 600
    step_ids = {s["id"] for s in fake.get_session(ref.session_id).structured_output["steps"]}
    for raw in fake.get_session(ref.session_id).structured_output["artifacts"]:
        assert normalise_artifact(raw, mission_id="m_1") is not None, raw["id"]
        assert raw["after_step"] in step_ids


def test_fake_messages_have_unique_ids_and_ordered_times(fake, ticker):
    ref = _start(fake)
    ticker.t += 600
    messages = fake.list_messages(ref.session_id)
    assert len({m.id for m in messages}) == len(messages)
    assert [m.at for m in messages] == sorted(m.at for m in messages)
    assert all(m.at.endswith("Z") for m in messages)


def test_fake_reply_gets_an_answer_and_one_more_artifact(fake, ticker):
    ref = _start(fake)
    ticker.t += 600
    before_artifacts = len(fake.get_session(ref.session_id).structured_output["artifacts"])
    before_texts = len(_devin_texts(fake, ref.session_id))

    fake.send_message(ref.session_id, "What about the outlier?")
    assert fake.get_session(ref.session_id).status == "running"
    assert [m.text for m in fake.list_messages(ref.session_id) if m.role == "user"][-1] == "What about the outlier?"

    ticker.t += 4
    assert len(_devin_texts(fake, ref.session_id)) == before_texts + 1
    assert fake.get_session(ref.session_id).status == "running"

    ticker.t += 60
    after = fake.get_session(ref.session_id)
    assert after.status == "waiting"
    assert len(after.structured_output["artifacts"]) == before_artifacts + 1


def test_fake_second_reply_adds_a_distinct_artifact(fake, ticker):
    ref = _start(fake)
    ticker.t += 600
    for text in ("one", "two"):
        fake.send_message(ref.session_id, text)
        ticker.t += 60
    ids = [a["id"] for a in fake.get_session(ref.session_id).structured_output["artifacts"]]
    assert len(ids) == len(set(ids)) == 9


def test_fake_sessions_are_independent(fake, ticker):
    first = _start(fake)
    ticker.t += 600
    second = _start(fake)
    assert fake.get_session(first.session_id).status == "waiting"
    assert fake.get_session(second.session_id).status == "running"


def test_fake_has_no_attachments_and_rejects_downloads(fake):
    ref = _start(fake)
    assert fake.list_attachments(ref.session_id) == []
    with pytest.raises(AttachmentRejected):
        fake.download(Attachment(name="x.png", url="https://x.test/x.png"))
    with pytest.raises(AttachmentRejected):
        fake.download_file(Attachment(name="x.zip", url="https://x.test/x.zip"))


# ---------- FakeDevin's final report ----------

def _finished(fake, ticker):
    ref = _start(fake)
    ticker.t += 600
    return ref.session_id


def test_fake_leaves_the_report_null_until_asked(fake, ticker):
    session_id = _finished(fake, ticker)
    assert fake.get_session(session_id).structured_output["report"] is None
    fake.send_message(session_id, "What about the outlier?")
    ticker.t += 60
    assert fake.get_session(session_id).structured_output["report"] is None


def test_fake_writes_the_report_two_beats_after_the_request(fake, ticker):
    session_id = _finished(fake, ticker)
    before = fake.get_session(session_id).structured_output
    texts = _devin_texts(fake, session_id)

    fake.send_message(session_id, REPORT_REQUEST)
    assert fake.get_session(session_id).status == "running"
    ticker.t += 5.9
    early = fake.get_session(session_id)
    assert (early.status, early.structured_output["report"]) == ("running", None)
    assert _devin_texts(fake, session_id) == texts

    ticker.t += 0.1
    ready = fake.get_session(session_id)
    assert ready.status == "waiting"
    assert ready.structured_output["report"] is not None
    assert {**ready.structured_output, "report": None} == before
    assert _devin_texts(fake, session_id) == [*texts, "The report is ready."]


def test_fake_does_not_treat_the_report_request_as_a_reply(fake, ticker):
    session_id = _finished(fake, ticker)
    artifacts = len(fake.get_session(session_id).structured_output["artifacts"])
    fake.send_message(session_id, REPORT_REQUEST)
    ticker.t += 60
    assert len(fake.get_session(session_id).structured_output["artifacts"]) == artifacts
    assert devin.REPLY_ACK not in _devin_texts(fake, session_id)
    assert [m.text for m in fake.list_messages(session_id) if m.role == "user"] == ["the brief", REPORT_REQUEST]


def test_fake_report_is_a_full_report_about_its_own_run(fake, ticker):
    session_id = _finished(fake, ticker)
    fake.send_message(session_id, REPORT_REQUEST)
    ticker.t += 60
    output = fake.get_session(session_id).structured_output
    raw = output["report"]
    artifacts = {a["id"]: a for a in output["artifacts"]}
    report = normalise_report(raw, set(artifacts))

    # Nothing is lost or reshaped by validation: the fake follows the brief to the letter.
    assert report["keyArtifactIds"] == raw["key_artifact_ids"] and len(raw["key_artifact_ids"]) == 3
    assert {(artifacts[i]["type"], artifacts[i].get("kind")) for i in raw["key_artifact_ids"]} >= {
        ("chart", "scatter"), ("relation", None)}
    assert report["headline"] == raw["headline"] and len(raw["headline"]) <= 70
    assert report["summary"] == raw["summary"] and 3 <= raw["summary"].count(". ") + 1 <= 5
    assert report["stats"] == raw["stats"] and len(raw["stats"]) == 4
    assert all(len(stat["value"]) <= 16 for stat in raw["stats"])
    assert report["steps"] == raw["steps"] and 5 <= len(raw["steps"]) <= 6
    assert all(2 <= len(step["label"].split()) <= 5 and step["takeaway"].endswith(".") for step in raw["steps"])
    assert report["caveats"] == raw["caveats"] and len(raw["caveats"]) == 2
    assert report["nextQuestions"] == raw["next_questions"] and len(raw["next_questions"]) == 2
    assert "*" not in repr(raw) and "#" not in repr(raw)


def test_fake_regenerates_a_visibly_different_report_each_time(fake, ticker):
    session_id = _finished(fake, ticker)
    summaries = []
    for _ in range(3):
        fake.send_message(session_id, REPORT_REQUEST)
        assert fake.get_session(session_id).status == "running"
        # Until the rewrite lands, the previous report is still what the output holds.
        previous = fake.get_session(session_id).structured_output["report"]
        assert (previous or {}).get("summary") == (summaries[-1] if summaries else None)
        ticker.t += 60
        assert fake.get_session(session_id).status == "waiting"
        summaries.append(fake.get_session(session_id).structured_output["report"]["summary"])
    assert len(set(summaries)) == 3
    assert "follow-up" in summaries[1]
    assert _devin_texts(fake, session_id).count("The report is ready.") == 3
    ids = [m.id for m in fake.list_messages(session_id)]
    assert len(ids) == len(set(ids))


def test_fake_handles_a_reply_and_a_report_request_together(fake, ticker):
    session_id = _finished(fake, ticker)
    fake.send_message(session_id, REPORT_REQUEST)
    ticker.t += 1
    fake.send_message(session_id, "What about the outlier?")
    ticker.t += 5
    assert fake.get_session(session_id).status == "running"
    ticker.t += 60
    after = fake.get_session(session_id)
    assert after.status == "waiting" and after.structured_output["report"] is not None
    assert after.structured_output["artifacts"][-1]["id"] == "r1"


def test_fake_forgets_a_report_across_a_restart_but_writes_one_when_asked_again(fake, ticker):
    session_id = _finished(fake, ticker)
    fake.send_message(session_id, REPORT_REQUEST)
    ticker.t += 60
    first = fake.get_session(session_id).structured_output["report"]

    restarted = FakeDevin(clock=ticker, beat_seconds=3.0)
    assert restarted.get_session(session_id).structured_output["report"] is None
    restarted.send_message(session_id, REPORT_REQUEST)
    ticker.t += 60
    assert restarted.get_session(session_id).structured_output["report"] == first


# ---------- FakeDevin's explorer ----------

def _ask(fake, session_id, instructions=None, next_version=None):
    fake.send_message(session_id, build_explorer_request(instructions, {"GUIDE.md": "the guide"},
                                                         next_version=next_version))


def test_fake_leaves_the_explorer_null_until_asked(fake, ticker):
    session_id = _finished(fake, ticker)
    assert fake.get_session(session_id).structured_output["explorer"] is None
    fake.send_message(session_id, REPORT_REQUEST)
    ticker.t += 60
    assert fake.get_session(session_id).structured_output["explorer"] is None
    assert fake.list_attachments(session_id) == []


def test_fake_builds_the_explorer_two_beats_after_the_request(fake, ticker):
    session_id = _finished(fake, ticker)
    before = fake.get_session(session_id).structured_output
    texts = _devin_texts(fake, session_id)

    _ask(fake, session_id)
    ticker.t += 5.9
    early = fake.get_session(session_id)
    assert (early.status, early.structured_output["explorer"]) == ("running", None)
    assert fake.list_attachments(session_id) == [] and _devin_texts(fake, session_id) == texts

    ticker.t += 0.1
    ready = fake.get_session(session_id)
    assert ready.status == "waiting"
    explorer = ready.structured_output["explorer"]
    assert set(explorer) == {"version", "archive", "entry", "title", "description"}
    assert (explorer["version"], explorer["archive"], explorer["entry"]) == (1, "explorer-v1.zip", "index.html")
    assert explorer["title"] and explorer["description"]
    assert {**ready.structured_output, "explorer": None} == before
    assert [a.name for a in fake.list_attachments(session_id)] == ["explorer-v1.zip"]
    assert _devin_texts(fake, session_id) == [*texts, "The explorer is ready."]


def test_fake_does_not_treat_the_explorer_request_as_a_reply(fake, ticker):
    session_id = _finished(fake, ticker)
    artifacts = len(fake.get_session(session_id).structured_output["artifacts"])
    _ask(fake, session_id, "Add a heatmap")
    ticker.t += 60
    output = fake.get_session(session_id).structured_output
    assert len(output["artifacts"]) == artifacts and output["report"] is None
    assert devin.REPLY_ACK not in _devin_texts(fake, session_id)
    users = [m.text for m in fake.list_messages(session_id) if m.role == "user"]
    assert users == ["the brief", build_explorer_request("Add a heatmap", {"GUIDE.md": "the guide"})]


def test_fake_archive_is_the_kits_worked_example_and_passes_the_unpacker(fake, ticker, kit, tmp_path):
    session_id = _finished(fake, ticker)
    _ask(fake, session_id)
    ticker.t += 60
    (attachment,) = fake.list_attachments(session_id)
    data = fake.download_file(attachment)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        # A copy of the kit rides along, as the protocol asks of Devin; the guide does not.
        assert sorted(archive.namelist()) == ["data.json", "index.html", "kit/kit.css", "kit/kit.js"]
    target = tmp_path / "explorers" / "m_1" / "1"
    assert unpack(data, target, entry="index.html") == ["data.json", "index.html"]
    assert (target / "index.html").read_text() == "<!doctype html><title>example</title>"


def test_fake_archive_is_built_when_it_is_asked_for_so_kit_edits_show(fake, ticker, kit):
    session_id = _finished(fake, ticker)
    _ask(fake, session_id)
    ticker.t += 60
    (attachment,) = fake.list_attachments(session_id)
    (kit / "index.html").write_text("<p>edited</p>")
    with zipfile.ZipFile(io.BytesIO(fake.download_file(attachment))) as archive:
        assert archive.read("index.html") == b"<p>edited</p>"


def test_fake_archive_from_the_real_kit_passes_the_unpacker(ticker, tmp_path):
    fake = FakeDevin(clock=ticker, beat_seconds=3.0)
    session_id = _finished(fake, ticker)
    _ask(fake, session_id)
    ticker.t += 60
    (attachment,) = fake.list_attachments(session_id)
    assert "index.html" in unpack(fake.download_file(attachment), tmp_path / "explorers" / "m_1" / "1")


def test_fake_bumps_the_version_on_every_request_and_shows_the_instructions(fake, ticker):
    session_id = _finished(fake, ticker)
    seen = []
    for instructions in (None, "Add a heatmap", "Colour by\n  score"):
        _ask(fake, session_id, instructions)
        assert fake.get_session(session_id).status == "running"
        ticker.t += 60
        assert fake.get_session(session_id).status == "waiting"
        seen.append(fake.get_session(session_id).structured_output["explorer"])
    assert [e["version"] for e in seen] == [1, 2, 3]
    assert [e["archive"] for e in seen] == ["explorer-v1.zip", "explorer-v2.zip", "explorer-v3.zip"]
    assert "Add a heatmap" not in seen[0]["description"] and seen[1]["description"].endswith("Add a heatmap")
    assert seen[2]["description"].endswith("Colour by score")
    assert [a.name for a in fake.list_attachments(session_id)] == [e["archive"] for e in seen]
    assert _devin_texts(fake, session_id).count("The explorer is ready.") == 3
    ids = [m.id for m in fake.list_messages(session_id)]
    assert len(ids) == len(set(ids))


def test_fake_uses_the_build_number_it_is_given_which_survives_a_restart(fake, ticker, kit):
    session_id = _finished(fake, ticker)
    _ask(fake, session_id, next_version=1)
    ticker.t += 60

    restarted = FakeDevin(clock=ticker, beat_seconds=3.0, kit_dir=kit)
    assert restarted.get_session(session_id).structured_output["explorer"] is None
    _ask(restarted, session_id, "Add a heatmap", next_version=2)
    ticker.t += 60
    assert restarted.get_session(session_id).structured_output["explorer"]["version"] == 2
    # A number that would not move the count on is ignored rather than repeated.
    _ask(restarted, session_id, next_version=2)
    ticker.t += 60
    assert restarted.get_session(session_id).structured_output["explorer"]["version"] == 3


def test_fake_handles_a_reply_a_report_and_an_explorer_request_together(fake, ticker):
    session_id = _finished(fake, ticker)
    fake.send_message(session_id, REPORT_REQUEST)
    _ask(fake, session_id)
    ticker.t += 1
    fake.send_message(session_id, "What about the outlier?")
    ticker.t += 5
    assert fake.get_session(session_id).status == "running"
    ticker.t += 60
    after = fake.get_session(session_id)
    assert after.status == "waiting"
    assert after.structured_output["report"] is not None and after.structured_output["explorer"]["version"] == 1
    assert after.structured_output["artifacts"][-1]["id"] == "r1"


@pytest.mark.parametrize("call", [
    lambda f: f.get_session("devin-nope"),
    lambda f: f.list_messages("devin-nope"),
    lambda f: f.send_message("devin-nope", "hi"),
    lambda f: f.list_attachments("devin-nope"),
])
def test_fake_unknown_session_is_unavailable(fake, call):
    with pytest.raises(DevinUnavailable):
        call(fake)


# ---------- make_client / env ----------

def test_make_client_without_a_key_is_the_fake(monkeypatch):
    monkeypatch.delenv("DEVIN_API_KEY", raising=False)
    client, demo = make_client()
    assert isinstance(client, FakeDevin) and demo is True


def test_make_client_with_blank_key_is_the_fake(monkeypatch):
    monkeypatch.setenv("DEVIN_API_KEY", "   ")
    client, demo = make_client()
    assert isinstance(client, FakeDevin) and demo is True


def test_make_client_forced_fake_even_with_a_key(monkeypatch):
    monkeypatch.setenv("DEVIN_API_KEY", KEY)
    monkeypatch.setenv("KINGDOM_FAKE_DEVIN", "1")
    client, demo = make_client()
    assert isinstance(client, FakeDevin) and demo is True


def test_make_client_with_a_key_is_v3(monkeypatch):
    monkeypatch.setenv("DEVIN_API_KEY", KEY)
    monkeypatch.setenv("KINGDOM_DEVIN_MODE", "lite")
    client, demo = make_client()
    assert isinstance(client, V3DevinClient) and demo is False
    assert client.mode == "lite"


@pytest.mark.parametrize("value, mode", [(None, "fast"), ("", "fast"), ("warp", "fast"), ("ultra", "ultra")])
def test_devin_mode_falls_back_to_fast(monkeypatch, value, mode):
    monkeypatch.setenv("DEVIN_API_KEY", KEY)
    if value is None:
        monkeypatch.delenv("KINGDOM_DEVIN_MODE", raising=False)
    else:
        monkeypatch.setenv("KINGDOM_DEVIN_MODE", value)
    assert make_client()[0].mode == mode


@pytest.mark.parametrize("value, expected", [(None, 5), ("", 5), ("3", 3), ("0", 5), ("-2", 5), ("lots", 5)])
def test_max_acu(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("KINGDOM_MAX_ACU", raising=False)
    else:
        monkeypatch.setenv("KINGDOM_MAX_ACU", value)
    assert max_acu() == expected


def test_client_repr_hides_the_key():
    assert KEY not in repr(V3DevinClient(KEY))


# ---------- V3DevinClient ----------

class Response:
    def __init__(self, status=200, body=None, *, text="", headers=None, chunks=None):
        self.status_code = status
        self._body = body
        self.text = text
        self.headers = headers or {}
        self._chunks = chunks or []
        self.closed = False

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body

    def iter_content(self, chunk_size=None):
        yield from self._chunks

    def close(self):
        self.closed = True


class Http:
    """Stands in for requests.request: replays queued responses and records calls."""

    def __init__(self, monkeypatch):
        self.calls: list[dict] = []
        self.queue: list = []
        monkeypatch.setattr(devin.requests, "request", self)

    def __call__(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def add(self, *items):
        self.queue.extend(items)
        return self


SELF = Response(body={"principal_type": "service_user", "org_id": ORG})


@pytest.fixture
def http(monkeypatch):
    return Http(monkeypatch)


@pytest.fixture
def client():
    return V3DevinClient(KEY, mode="fast", sleep=lambda seconds: None)


def test_create_session_request_and_response(http, client):
    http.add(SELF, Response(body={"session_id": "devin-abc", "url": "https://app.devin.ai/sessions/abc", "status": "new"}))
    ref = client.create_session("prompt text", title="Kingdom: T", schema={"type": "object"}, max_acu=4)

    assert ref == SessionRef("devin-abc", "https://app.devin.ai/sessions/abc")
    me, create = http.calls
    assert (me["method"], me["url"]) == ("GET", "https://api.devin.ai/v3/self")
    assert (create["method"], create["url"]) == ("POST", f"{BASE}/sessions")
    assert create["json"] == {
        "prompt": "prompt text",
        "title": "Kingdom: T",
        "max_acu_limit": 4,
        "devin_mode": "fast",
        "structured_output_schema": {"type": "object"},
    }
    for call in http.calls:
        assert call["headers"]["Authorization"] == f"Bearer {KEY}"
        assert call["timeout"]


def test_create_session_without_url_is_tolerated(http, client):
    http.add(SELF, Response(body={"session_id": "devin-abc"}))
    assert client.create_session("p", title="t", schema={}, max_acu=1) == SessionRef("devin-abc", None)


@pytest.mark.parametrize("body", [{}, {"session_id": ""}, {"session_id": 7}, ["x"], None])
def test_create_session_bad_response_is_unavailable(http, client, body):
    http.add(SELF, Response(body=body))
    with pytest.raises(DevinUnavailable):
        client.create_session("p", title="t", schema={}, max_acu=1)


def test_org_id_is_resolved_once(http, client):
    http.add(SELF, Response(body={"status": "running"}), Response(body={"status": "running"}))
    client.get_session("devin-abc")
    client.get_session("devin-abc")
    assert [c["url"] for c in http.calls] == [
        "https://api.devin.ai/v3/self", f"{BASE}/sessions/devin-abc", f"{BASE}/sessions/devin-abc"]


@pytest.mark.parametrize("body", [{}, {"org_id": ""}, {"org_id": None}, "nope"])
def test_self_without_org_is_unavailable_and_not_cached(http, client, body):
    http.add(Response(body=body))
    with pytest.raises(DevinUnavailable):
        client.get_session("devin-abc")
    http.add(SELF, Response(body={"status": "running"}))
    assert client.get_session("devin-abc").status == "running"


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retries_once_on_throttle_or_server_error(http, client, status):
    http.add(SELF, Response(status, text="slow down"), Response(body={"status": "running"}))
    assert client.get_session("devin-abc").status == "running"
    assert len(http.calls) == 3


def test_gives_up_after_the_second_failure(http, client):
    http.add(SELF, Response(503, text="down"), Response(503, text="still down"))
    with pytest.raises(DevinUnavailable) as error:
        client.get_session("devin-abc")
    assert "503" in str(error.value) and "still down" in str(error.value)
    assert len(http.calls) == 3


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_client_errors_are_not_retried(http, client, status):
    http.add(SELF, Response(status, text="nope"))
    with pytest.raises(DevinUnavailable) as error:
        client.get_session("devin-abc")
    assert str(status) in str(error.value)
    assert len(http.calls) == 2


def test_network_errors_are_unavailable_and_never_leak_the_key(http, client):
    http.add(requests.ConnectionError("connection refused"))
    with pytest.raises(DevinUnavailable) as error:
        client.get_session("devin-abc")
    assert "connection refused" in str(error.value)
    assert KEY not in str(error.value)


def test_error_detail_is_truncated(http, client):
    http.add(SELF, Response(400, text="x" * 5000))
    with pytest.raises(DevinUnavailable) as error:
        client.get_session("devin-abc")
    assert len(str(error.value)) < 500


def test_invalid_json_is_unavailable(http, client):
    http.add(SELF, Response(body=None))
    with pytest.raises(DevinUnavailable):
        client.get_session("devin-abc")


@pytest.mark.parametrize("status, detail, expected", [
    ("new", None, "running"),
    ("claimed", None, "running"),
    ("running", None, "running"),
    ("running", "working", "running"),
    ("running", "waiting_for_user", "waiting"),
    ("running", "waiting_for_approval", "waiting"),
    ("running", "finished", "finished"),
    ("resuming", None, "running"),
    ("exit", None, "finished"),
    ("suspended", None, "waiting"),
    ("suspended", "inactivity", "waiting"),
    ("suspended", "user_request", "waiting"),
    ("suspended", "usage_limit_exceeded", "error"),
    ("suspended", "out_of_credits", "error"),
    ("suspended", "out_of_quota", "error"),
    ("suspended", "no_quota_allocation", "error"),
    ("suspended", "payment_declined", "error"),
    ("suspended", "org_usage_limit_exceeded", "error"),
    ("suspended", "user_usage_limit_exceeded", "error"),
    ("suspended", "total_session_limit_exceeded", "error"),
    ("suspended", "error", "error"),
    ("error", None, "error"),
    ("error", "working", "error"),
    ("something_new", None, "running"),
    ("running", "something_new", "running"),
    (None, None, "running"),
    ("RUNNING", "Waiting_For_User", "waiting"),
])
def test_status_normalisation(http, client, status, detail, expected):
    http.add(SELF, Response(body={"status": status, "status_detail": detail}))
    assert client.get_session("devin-abc").status == expected


def test_snapshot_detail_and_structured_output(http, client):
    output = {"steps": []}
    http.add(SELF, Response(body={"status": "suspended", "status_detail": "out_of_credits", "structured_output": output}))
    snapshot = client.get_session("devin-abc")
    assert snapshot.detail == "out_of_credits"
    assert snapshot.structured_output == output


@pytest.mark.parametrize("output", ["a string", ["list"], 3, None])
def test_non_object_structured_output_becomes_none(http, client, output):
    http.add(SELF, Response(body={"status": "running", "structured_output": output}))
    assert client.get_session("devin-abc").structured_output is None


def test_list_messages_documented_shape(http, client):
    http.add(SELF, Response(body={"items": [
        {"event_id": "ev1", "source": "user", "message": "the brief", "created_at": 1_790_000_000},
        {"event_id": "ev2", "source": "devin", "message": "Reading the data", "created_at": 1_790_000_060},
    ], "has_next_page": False, "end_cursor": None}))
    messages = client.list_messages("devin-abc")
    assert messages == [
        DevinMessage("ev1", "user", "the brief", "2026-09-21T14:13:20Z"),
        DevinMessage("ev2", "devin", "Reading the data", "2026-09-21T14:14:20Z"),
    ]
    assert http.calls[1]["url"] == f"{BASE}/sessions/devin-abc/messages"


def test_list_messages_follows_pages(http, client):
    http.add(
        SELF,
        Response(body={"items": [{"event_id": "1", "source": "devin", "message": "a"}], "has_next_page": True, "end_cursor": "c1"}),
        Response(body={"items": [{"event_id": "2", "source": "devin", "message": "b"}], "has_next_page": False}),
    )
    assert [m.id for m in client.list_messages("devin-abc")] == ["1", "2"]
    assert http.calls[2]["params"]["after"] == "c1"


def test_list_messages_stops_when_a_page_has_no_cursor(http, client):
    http.add(SELF, Response(body={"items": [{"event_id": "1", "message": "a"}], "has_next_page": True, "end_cursor": None}))
    assert len(client.list_messages("devin-abc")) == 1


def test_list_messages_bare_list_and_unknown_fields(http, client):
    http.add(SELF, Response(body=[
        {"id": 42, "role": "assistant", "content": "hello", "timestamp": "2026-09-20T12:00:00Z", "weird": {"x": 1}},
        "junk",
        {"type": "user_message", "text": "hi"},
        {"message": ""},
        {"message": None},
    ]))
    messages = client.list_messages("devin-abc")
    assert [(m.id, m.role, m.text, m.at) for m in messages] == [
        ("42", "devin", "hello", "2026-09-20T12:00:00Z"),
        ("2:", "user", "hi", ""),
    ]


@pytest.mark.parametrize("fields, role", [
    ({"source": "user"}, "user"),
    ({"source": "devin"}, "devin"),
    ({"role": "human"}, "user"),
    ({"type": "initial_user_message"}, "user"),
    ({"type": "devin_message"}, "devin"),
    ({"origin": "api"}, "devin"),
    ({"sender": "user"}, "user"),
    ({"source": "DEVIN", "origin": "api"}, "devin"),
    ({"username": "tom"}, "devin"),
    ({}, "devin"),
    ({"source": 7}, "devin"),
])
def test_message_role_is_derived_defensively(http, client, fields, role):
    http.add(SELF, Response(body={"items": [{"event_id": "e", "message": "text", **fields}]}))
    assert client.list_messages("devin-abc")[0].role == role


@pytest.mark.parametrize("created, expected", [
    (1_790_000_000, "2026-09-21T14:13:20Z"),
    (1_790_000_000_000, "2026-09-21T14:13:20Z"),
    (1_790_000_000.7, "2026-09-21T14:13:20Z"),
    ("2026-09-20T12:00:00+00:00", "2026-09-20T12:00:00Z"),
    ("2026-09-20T14:00:00+02:00", "2026-09-20T12:00:00Z"),
    ("not a date", ""),
    (None, ""),
    (True, ""),
])
def test_message_timestamps(http, client, created, expected):
    http.add(SELF, Response(body={"items": [{"event_id": "e", "message": "t", "created_at": created}]}))
    assert client.list_messages("devin-abc")[0].at == expected


@pytest.mark.parametrize("body", [{"items": "nope"}, {"data": []}, "text", 3])
def test_list_messages_unexpected_body_is_empty(http, client, body):
    http.add(SELF, Response(body=body))
    assert client.list_messages("devin-abc") == []


def test_send_message(http, client):
    http.add(SELF, Response(body={}))
    assert client.send_message("devin-abc", "Drop it") is None
    call = http.calls[1]
    assert (call["method"], call["url"], call["json"]) == (
        "POST", f"{BASE}/sessions/devin-abc/messages", {"message": "Drop it"})


def test_send_message_tolerates_an_empty_body(http, client):
    http.add(SELF, Response(status=204, body=None))
    client.send_message("devin-abc", "ok")


def test_list_attachments(http, client):
    http.add(SELF, Response(body={"items": [
        {"attachment_id": "att1", "content_type": "image/png", "name": "plot.png", "source": "devin",
         "url": "https://app.devin.ai/attachments/att1/plot.png"},
        {"name": "old.png", "url": "https://files.test/old.png"},
        {"name": "idonly.zip", "attachment_id": "att2", "url": None},
        {"name": "badid.png", "attachment_id": 7, "url": "https://files.test/badid.png"},
        {"name": "", "url": "https://files.test/x"},
        {"name": "nourl.png"},
        "junk",
    ]}))
    assert client.list_attachments("devin-abc") == [
        Attachment("plot.png", "https://app.devin.ai/attachments/att1/plot.png", "att1"),
        Attachment("old.png", "https://files.test/old.png"),
        Attachment("idonly.zip", "", "att2"),
        Attachment("badid.png", "https://files.test/badid.png"),
    ]
    assert http.calls[1]["url"] == f"{BASE}/sessions/devin-abc/attachments"


def test_session_ids_are_escaped_in_urls(http, client):
    http.add(SELF, Response(body={"status": "running"}))
    client.get_session("../../self")
    assert http.calls[1]["url"] == f"{BASE}/sessions/..%2F..%2Fself"


# ---------- attachment download ----------

def _png(size=10):
    return Response(headers={"Content-Type": "image/png"}, chunks=[b"x" * size])


def test_download_returns_image_bytes_without_credentials_for_foreign_hosts(http, client):
    http.add(_png())
    data, content_type = client.download(Attachment("plot.png", "https://bucket.s3.amazonaws.com/plot.png?sig=1"))
    assert (data, content_type) == (b"x" * 10, "image/png")
    call = http.calls[0]
    assert call["method"] == "GET" and call["stream"] is True
    assert "Authorization" not in (call.get("headers") or {})


@pytest.mark.parametrize("url", ["https://api.devin.ai/attachments/1", "https://files.devin.ai/a/plot.png"])
def test_download_sends_credentials_to_devin_hosts(http, client, url):
    http.add(_png())
    client.download(Attachment("plot.png", url))
    assert http.calls[0]["headers"]["Authorization"] == f"Bearer {KEY}"


@pytest.mark.parametrize("url", [
    "https://devin.ai.evil.test/plot.png",
    "https://evildevin.ai/plot.png",
    "https://api.devin.ai@evil.test/plot.png",
])
def test_download_does_not_trust_lookalike_hosts(http, client, url):
    http.add(_png())
    client.download(Attachment("plot.png", url))
    assert "Authorization" not in (http.calls[0].get("headers") or {})


@pytest.mark.parametrize("url", ["http://api.devin.ai/plot.png", "file:///etc/passwd", "ftp://x.test/a", "", "nonsense"])
def test_download_refuses_non_https(http, client, url):
    with pytest.raises(AttachmentRejected):
        client.download(Attachment("plot.png", url))
    assert http.calls == []


@pytest.mark.parametrize("content_type", ["text/html", "application/pdf", "image/svg+xml", "", None])
def test_download_refuses_non_images(http, client, content_type):
    headers = {} if content_type is None else {"Content-Type": content_type}
    response = Response(headers=headers, chunks=[b"<html>"])
    http.add(response)
    with pytest.raises(AttachmentRejected):
        client.download(Attachment("plot.png", "https://files.test/plot.png"))
    assert response.closed


def test_download_strips_content_type_parameters(http, client):
    http.add(Response(headers={"Content-Type": "IMAGE/JPEG; charset=binary"}, chunks=[b"j"]))
    assert client.download(Attachment("a.jpg", "https://files.test/a.jpg"))[1] == "image/jpeg"


def test_download_enforces_the_size_cap_while_streaming(http, client):
    chunk = b"x" * (1024 * 1024)
    response = Response(headers={"Content-Type": "image/png"}, chunks=[chunk] * 11)
    http.add(response)
    with pytest.raises(AttachmentRejected):
        client.download(Attachment("big.png", "https://files.test/big.png"))
    assert response.closed


def test_download_refuses_a_declared_oversize_without_reading(http, client):
    http.add(Response(headers={"Content-Type": "image/png", "Content-Length": str(11 * 1024 * 1024)}, chunks=[b"x"]))
    with pytest.raises(AttachmentRejected):
        client.download(Attachment("big.png", "https://files.test/big.png"))


def test_download_accepts_exactly_the_cap(http, client):
    http.add(Response(headers={"Content-Type": "image/png"}, chunks=[b"x" * devin.MAX_ATTACHMENT_BYTES]))
    assert len(client.download(Attachment("ok.png", "https://files.test/ok.png"))[0]) == devin.MAX_ATTACHMENT_BYTES


@pytest.mark.parametrize("failure", [Response(404, text="gone"), requests.Timeout("slow")])
def test_download_failures_are_rejections(http, client, failure):
    http.add(failure)
    with pytest.raises(AttachmentRejected):
        client.download(Attachment("plot.png", "https://files.test/plot.png"))


@pytest.mark.parametrize("failure, passing", [
    (Response(404, text="gone"), False), (Response(401), False), (Response(403), False),
    (Response(429), True), (Response(500), True), (Response(503), True),
    (requests.Timeout("slow"), True), (requests.ConnectionError("reset"), True),
])
def test_download_failures_say_whether_a_retry_could_help(http, client, failure, passing):
    http.add(failure)
    with pytest.raises(AttachmentRejected) as caught:
        client.download_file(Attachment("site.zip", "https://files.test/site.zip"))
    assert isinstance(caught.value, AttachmentUnavailable) is passing
    assert KEY not in str(caught.value)
    if isinstance(failure, Response):
        assert failure.closed


def test_a_connection_that_drops_mid_download_is_worth_a_retry(http, client):
    class Dropping(Response):
        def iter_content(self, chunk_size=None):
            yield b"PK"
            raise requests.ConnectionError("reset")

    http.add(Dropping())
    with pytest.raises(AttachmentUnavailable):
        client.download_file(Attachment("site.zip", "https://files.test/site.zip"))


# ---------- attachment download: the API route and its redirect ----------

LISTED = Attachment("plot 1.png", "https://app.devin.ai/attachments/att-1/plot%201.png", "att-1")
ROUTE = f"{BASE}/attachments/att-1/plot%201.png"
SIGNED = "https://devin-files.s3.amazonaws.com/att-1/plot.png?X-Amz-Signature=abc"


def _redirect(location, status=307):
    return Response(status, headers={} if location is None else {"Location": location})


def _authorised(call):
    return (call.get("headers") or {}).get("Authorization") == f"Bearer {KEY}"


def test_download_goes_through_the_api_route_and_follows_its_redirect_without_the_key(http, client):
    hop = _redirect(SIGNED)
    http.add(SELF, hop, _png())
    assert client.download(LISTED) == (b"x" * 10, "image/png")
    api, storage = http.calls[1:]
    assert (api["method"], api["url"], api["allow_redirects"], api["stream"]) == ("GET", ROUTE, False, True)
    assert _authorised(api)
    assert (storage["url"], storage["allow_redirects"]) == (SIGNED, False)
    assert "Authorization" not in (storage.get("headers") or {})
    assert hop.closed
    # The web-app link that rejects API keys is never requested.
    assert all("app.devin.ai" not in call["url"] for call in http.calls)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_download_follows_every_kind_of_redirect(http, client, status):
    http.add(SELF, _redirect(SIGNED, status), _png())
    assert client.download(LISTED)[0] == b"x" * 10


def test_download_without_an_attachment_id_takes_it_from_the_listed_url(http, client):
    http.add(SELF, _redirect(SIGNED), _png())
    client.download(Attachment("plot 1.png", "https://app.devin.ai/attachments/att-1/plot%201.png"))
    assert http.calls[1]["url"] == ROUTE


def test_download_uses_the_attachment_name_not_the_one_in_the_url(http, client):
    http.add(SELF, _png())
    client.download(Attachment("../self", "https://app.devin.ai/attachments/a%2Fb/other.png"))
    assert http.calls[1]["url"] == f"{BASE}/attachments/a%2Fb/..%2Fself"


@pytest.mark.parametrize("url", [
    "https://app.devin.ai/attachments/att-1",
    "https://app.devin.ai/files/att-1/plot.png",
    "https://app.devin.ai/attachments/att-1/nested/plot.png",
    "https://evil.test/attachments/att-1/plot.png",
    "https://app.devin.ai.evil.test/attachments/att-1/plot.png",
])
def test_download_falls_back_to_the_listed_url_when_it_holds_no_attachment_id(http, client, url):
    http.add(_png())
    client.download(Attachment("plot.png", url))
    assert [call["url"] for call in http.calls] == [url]


def test_download_with_only_an_attachment_id_needs_no_url(http, client):
    http.add(SELF, _redirect(SIGNED), _png())
    assert client.download(Attachment("plot 1.png", "", "att-1"))[0] == b"x" * 10
    assert http.calls[1]["url"] == ROUTE


def test_download_follows_a_relative_redirect_on_devin_with_the_key(http, client):
    http.add(SELF, _redirect("/v3/files/att-1"), _png())
    client.download(LISTED)
    assert http.calls[2]["url"] == "https://api.devin.ai/v3/files/att-1"
    assert _authorised(http.calls[2])


def test_the_key_never_comes_back_once_the_chain_has_left_devin(http, client):
    http.add(SELF, _redirect(SIGNED), _redirect("https://api.devin.ai/v3/self"), _png())
    client.download(LISTED)
    assert [_authorised(call) for call in http.calls[1:]] == [True, False, False]


@pytest.mark.parametrize("location", [
    "http://devin-files.s3.amazonaws.com/plot.png", "ftp://files.test/plot.png", "file:///etc/passwd",
    "javascript:alert(1)",
])
def test_download_refuses_a_redirect_that_is_not_https(http, client, location):
    http.add(SELF, _redirect(location))
    with pytest.raises(AttachmentRejected) as caught:
        client.download(LISTED)
    assert not isinstance(caught.value, AttachmentUnavailable)
    assert len(http.calls) == 2


@pytest.mark.parametrize("location", [None, ""])
def test_download_refuses_a_redirect_without_a_location(http, client, location):
    http.add(SELF, _redirect(location))
    with pytest.raises(AttachmentRejected):
        client.download(LISTED)


def test_download_gives_up_on_a_redirect_loop(http, client):
    hops = [_redirect(SIGNED) for _ in range(devin.MAX_REDIRECTS + 1)]
    http.add(SELF, *hops)
    with pytest.raises(AttachmentRejected, match="too many"):
        client.download(LISTED)
    assert len(http.calls) == 1 + devin.MAX_REDIRECTS + 1
    assert all(hop.closed for hop in hops)


def test_download_allows_as_many_hops_as_the_limit(http, client):
    http.add(SELF, *[_redirect(SIGNED) for _ in range(devin.MAX_REDIRECTS)], _png())
    assert client.download(LISTED)[0] == b"x" * 10


def test_redirected_downloads_keep_every_image_rule(http, client):
    http.add(SELF, _redirect(SIGNED), Response(headers={"Content-Type": "image/svg+xml"}, chunks=[b"<svg/>"]))
    with pytest.raises(AttachmentRejected):
        client.download(LISTED)
    http.add(_redirect(SIGNED), Response(headers={"Content-Type": "image/png"}, chunks=[b"x" * 1024 * 1024] * 11))
    with pytest.raises(AttachmentRejected, match="10 MB"):
        client.download(LISTED)


def test_download_when_the_organisation_lookup_fails_is_unavailable(http, client):
    http.add(Response(503), Response(503))
    with pytest.raises(DevinUnavailable):
        client.download(LISTED)


# ---------- file download ----------

ARCHIVE = Attachment("explorer-v1.zip", "https://app.devin.ai/attachments/att-9/explorer-v1.zip", "att-9")


def test_download_file_returns_bytes_of_any_type_by_the_same_safe_route(http, client):
    http.add(SELF, _redirect(SIGNED), Response(headers={"Content-Type": "application/zip"}, chunks=[b"PK", b"\x03\x04"]))
    assert client.download_file(ARCHIVE) == b"PK\x03\x04"
    api, storage = http.calls[1:]
    assert api["url"] == f"{BASE}/attachments/att-9/explorer-v1.zip" and _authorised(api)
    assert not _authorised(storage) and storage["allow_redirects"] is False


def test_download_file_needs_no_content_type(http, client):
    http.add(SELF, Response(chunks=[b"data"]))
    assert client.download_file(ARCHIVE) == b"data"


def test_download_file_enforces_its_own_cap_while_streaming(http, client):
    response = Response(chunks=[b"x" * (1024 * 1024)] * 41)
    http.add(SELF, response)
    with pytest.raises(AttachmentRejected, match="40 MB") as caught:
        client.download_file(ARCHIVE)
    assert response.closed and not isinstance(caught.value, AttachmentUnavailable)


def test_download_file_refuses_a_declared_oversize_without_reading(http, client):
    class Unreadable(Response):
        def iter_content(self, chunk_size=None):
            raise AssertionError("read anyway")

    http.add(SELF, Unreadable(headers={"Content-Length": str(devin.MAX_ARCHIVE_BYTES + 1)}))
    with pytest.raises(AttachmentRejected, match="40 MB"):
        client.download_file(ARCHIVE)


def test_download_file_accepts_exactly_the_cap(http, client):
    http.add(SELF, Response(chunks=[b"x" * devin.MAX_ARCHIVE_BYTES]))
    assert len(client.download_file(ARCHIVE)) == devin.MAX_ARCHIVE_BYTES


def test_download_file_refuses_non_https(http, client):
    with pytest.raises(AttachmentRejected):
        client.download_file(Attachment("site.zip", "http://files.test/site.zip"))
    assert http.calls == []


# ---------- FakeDevin across restarts ----------

def test_fake_picks_a_session_back_up_after_a_restart(fake, ticker):
    ref = _start(fake)
    ticker.t += 600
    before = fake.get_session(ref.session_id)

    restarted = FakeDevin(clock=ticker, beat_seconds=3.0)
    after = restarted.get_session(ref.session_id)
    assert (after.status, after.structured_output) == (before.status, before.structured_output)
    assert _devin_texts(restarted, ref.session_id) == _devin_texts(fake, ref.session_id)


def test_fake_resumes_mid_run_where_the_clock_says(fake, ticker):
    ref = _start(fake)
    ticker.t += 7
    restarted = FakeDevin(clock=ticker, beat_seconds=3.0)
    assert restarted.get_session(ref.session_id).status == "running"
    assert restarted.get_session(ref.session_id).structured_output == fake.get_session(ref.session_id).structured_output


def test_fake_accepts_a_reply_after_a_restart(fake, ticker):
    ref = _start(fake)
    ticker.t += 600
    restarted = FakeDevin(clock=ticker, beat_seconds=3.0)
    restarted.send_message(ref.session_id, "And without the first month?")
    assert restarted.get_session(ref.session_id).status == "running"
    ticker.t += 60
    assert restarted.get_session(ref.session_id).status == "waiting"


def test_fake_ids_stay_unique_across_restarts(fake, ticker):
    first = _start(fake)
    restarted = FakeDevin(clock=ticker, beat_seconds=3.0)
    assert _start(restarted).session_id != first.session_id


@pytest.mark.parametrize("session_id", ["devin-abc123", "devin-demo-", "devin-demo-notanumber-1", "", "devin-demo-1"])
def test_fake_rejects_ids_it_could_not_have_issued(fake, session_id):
    with pytest.raises(DevinUnavailable):
        fake.get_session(session_id)
