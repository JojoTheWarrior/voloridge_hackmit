"""Tests for server.app: every route, with a scripted Devin and a real SQLite store."""
from __future__ import annotations

import io
import zipfile

import pytest

from server.app import create_app, explorer_csp
from server.brief import EXPLORER_OPENING, REPORT_REQUEST, build_explorer_request
from server.devin import Attachment, AttachmentRejected, DevinUnavailable, FakeDevin, SessionRef
from server.poller import Poller
from server.explorer import unpack
from server.store import Store
from server.sync import SyncResult

HYPOTHESIS = "Do satellite images of storm damage predict how long power outages last?"


class StubDevin:
    def __init__(self):
        self.created: list[dict] = []
        self.sent: list[tuple[str, str]] = []
        self.attachments = [Attachment("plot.png", "https://files.test/plot.png")]
        self.downloads: dict[str, tuple[bytes, str] | Exception] = {"plot.png": (b"PNGDATA", "image/png")}
        self.create_error: Exception | None = None
        self.send_error: Exception | None = None
        self.attachments_error: Exception | None = None

    def create_session(self, prompt, *, title, schema, max_acu):
        if self.create_error:
            raise self.create_error
        self.created.append({"prompt": prompt, "title": title, "schema": schema, "max_acu": max_acu})
        return SessionRef("devin-abc", "https://app.devin.ai/sessions/devin-abc")

    def send_message(self, session_id, text):
        if self.send_error:
            raise self.send_error
        self.sent.append((session_id, text))

    def list_attachments(self, session_id):
        if self.attachments_error:
            raise self.attachments_error
        return self.attachments

    def download(self, attachment):
        result = self.downloads[attachment.name]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "k.db")


@pytest.fixture
def devin():
    return StubDevin()


@pytest.fixture
def kit(tmp_path):
    """A stand-in kit: the real one is someone else's to change, so no test here reads it."""
    root = tmp_path / "kit"
    root.mkdir()
    for name, text in {"GUIDE.md": "KIT-GUIDE-TEXT", "kit.css": "body { color: canonical }", "kit.js": "KIT-JS",
                       "index.html": "<!doctype html><title>EXAMPLE-PAGE</title>", "data.json": '{"rows": [1]}'}.items():
        (root / name).write_text(text)
    return root


@pytest.fixture
def client(store, devin, kit):
    return create_app(store, devin, demo=False, kit_dir=kit).test_client()


def _create(client, **over):
    body = {"hypothesis": HYPOTHESIS, "datasetIds": ["gdelt"]}
    body.update(over)
    return client.post("/api/missions", json=body)


# ---------- meta ----------

@pytest.mark.parametrize("demo", [True, False])
def test_meta(store, devin, demo):
    response = create_app(store, devin, demo=demo).test_client().get("/api/meta")
    assert response.status_code == 200
    assert response.get_json()["demo"] is demo


def test_meta_reports_the_acu_cap_and_mode(store, devin, monkeypatch):
    monkeypatch.setenv("KINGDOM_MAX_ACU", "3")
    monkeypatch.setenv("KINGDOM_DEVIN_MODE", "lite")
    body = create_app(store, devin, demo=True).test_client().get("/api/meta").get_json()
    assert body == {"demo": True, "maxAcu": 3, "devinMode": "lite"}


# ---------- create ----------

def test_create_mission(client, devin, store, monkeypatch):
    monkeypatch.setenv("KINGDOM_MAX_ACU", "2")
    response = _create(client)
    assert response.status_code == 201
    mission = response.get_json()

    assert set(mission) == {"id", "title", "hypothesis", "status", "createdAt", "updatedAt", "datasetIds",
                            "sessionUrl", "reportPending", "explorerPending", "events"}
    assert (mission["reportPending"], mission["explorerPending"]) == (False, False)
    assert mission["id"].startswith("m_")
    assert mission["title"] == "Do satellite images of storm damage predict how long power outages last"
    assert mission["hypothesis"] == HYPOTHESIS
    assert mission["status"] == "working"
    assert mission["datasetIds"] == ["gdelt"]
    assert mission["sessionUrl"] == "https://app.devin.ai/sessions/devin-abc"
    assert [(e["kind"], e["text"]) for e in mission["events"]] == [("user_message", HYPOTHESIS)]
    assert mission["createdAt"].endswith("Z")

    (created,) = devin.created
    assert created["title"] == f"Kingdom: {mission['title']}"
    assert created["max_acu"] == 2
    assert created["schema"]["properties"].keys() >= {"steps", "artifacts", "conclusion", "needs_user"}
    assert HYPOTHESIS in created["prompt"] and "https://www.gdeltproject.org" in created["prompt"]
    assert store.get_mission(mission["id"]).session_id == "devin-abc"


def test_create_trims_the_hypothesis(client):
    assert _create(client, hypothesis=f"  {HYPOTHESIS} \n").get_json()["hypothesis"] == HYPOTHESIS


def test_reference_reaches_devin_but_is_never_returned(client, devin):
    secret = "Prior run found r=0.42 at lag 3 using CAMEO 19x."
    created = _create(client, reference=secret).get_json()
    assert secret in devin.created[0]["prompt"]

    fetched = client.get(f"/api/missions/{created['id']}")
    listed = client.get("/api/missions")
    for response in (fetched, listed):
        assert secret not in response.get_data(as_text=True)
    assert "reference" not in created and "prompt" not in created


@pytest.mark.parametrize("body", [{}, {"hypothesis": ""}, {"hypothesis": "   "}, {"hypothesis": None},
                                  {"hypothesis": 7}, {"datasetIds": ["gdelt"]}])
def test_create_without_a_hypothesis_is_422(client, devin, body):
    response = client.post("/api/missions", json=body)
    assert response.status_code == 422
    assert response.get_json() == {"field": "hypothesis", "message": "Describe a connection to test"}
    assert devin.created == []
    assert client.get("/api/missions").get_json() == []


@pytest.mark.parametrize("raw", [b"", b"not json", b"[1, 2]", b'"text"'])
def test_create_with_a_non_object_body_is_422(client, raw):
    response = client.post("/api/missions", data=raw, content_type="application/json")
    assert response.status_code == 422
    assert response.get_json()["field"] == "hypothesis"


@pytest.mark.parametrize("dataset_ids, expected", [
    (None, []), ("gdelt", []), ([], []), (["ghost"], []), ([7, None, "yahoo"], ["yahoo"]),
    (["yahoo", "gdelt", "yahoo"], ["yahoo", "gdelt"]),
])
def test_create_keeps_only_known_dataset_ids(client, dataset_ids, expected):
    assert _create(client, datasetIds=dataset_ids).get_json()["datasetIds"] == expected


def test_create_with_a_blank_reference_sends_no_reference_section(client, devin):
    _create(client, reference="   ")
    _create(client, reference=42)
    assert all("private notes" not in created["prompt"].lower() for created in devin.created)


def test_create_with_devin_down_returns_a_failed_mission_not_a_5xx(client, devin):
    devin.create_error = DevinUnavailable("Devin session creation failed (503): upstream sad")
    response = _create(client)
    assert response.status_code == 201
    mission = response.get_json()
    assert mission["status"] == "failed"
    assert "sessionUrl" not in mission
    assert [e["kind"] for e in mission["events"]] == ["user_message", "error"]
    assert "503" in mission["events"][1]["text"]
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "failed"


# ---------- read ----------

def test_list_missions_is_newest_first_summaries(client):
    first = _create(client, hypothesis="First question?").get_json()
    second = _create(client, hypothesis="Second question?").get_json()
    listed = client.get("/api/missions").get_json()
    assert [m["id"] for m in listed] == [second["id"], first["id"]]
    assert set(listed[0]) == {"id", "title", "hypothesis", "status", "createdAt", "updatedAt"}


def test_get_unknown_mission_is_404(client):
    response = client.get("/api/missions/m_nope")
    assert response.status_code == 404
    assert response.get_json() == {"message": "Mission not found"}


def test_get_mission_includes_needs_user_only_when_set(client, store):
    mission = _create(client).get_json()
    assert "needsUser" not in mission
    store.apply_sync(mission["id"], SyncResult([], [], "waiting", "Drop the outlier?"), expected_status="working")
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["needsUser"]) == ("waiting", "Drop the outlier?")


# ---------- messages ----------

def test_send_message(client, devin):
    mission = _create(client).get_json()
    response = client.post(f"/api/missions/{mission['id']}/messages", json={"text": "  Drop the outlier  "})
    assert response.status_code == 202
    assert response.get_json() == {}
    assert devin.sent == [("devin-abc", "Drop the outlier")]
    events = client.get(f"/api/missions/{mission['id']}").get_json()["events"]
    assert [(e["kind"], e["text"]) for e in events][-1] == ("user_message", "Drop the outlier")


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": " \n "}, {"text": None}, {"text": 3}])
def test_send_blank_message_is_422(client, devin, body):
    mission = _create(client).get_json()
    response = client.post(f"/api/missions/{mission['id']}/messages", json=body)
    assert response.status_code == 422
    assert response.get_json() == {"field": "text", "message": "Write a reply"}
    assert devin.sent == []


def test_send_message_to_unknown_mission_is_404(client):
    response = client.post("/api/missions/m_nope/messages", json={"text": "hi"})
    assert response.status_code == 404
    assert response.get_json() == {"message": "Mission not found"}


def test_reply_reopens_a_done_mission(client):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/done")
    assert client.post(f"/api/missions/{mission['id']}/messages", json={"text": "One more thing"}).status_code == 202
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "working"


def test_reply_clears_the_question_it_answers(client, store):
    mission = _create(client).get_json()
    store.apply_sync(mission["id"], SyncResult([], [], "waiting", "Drop it?"), expected_status="working")
    client.post(f"/api/missions/{mission['id']}/messages", json={"text": "Yes"})
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert fetched["status"] == "working" and "needsUser" not in fetched


def test_reply_when_devin_is_down_is_shown_in_the_thread_and_does_not_reopen(client, devin):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/done")
    devin.send_error = DevinUnavailable("Devin message failed (503)")
    response = client.post(f"/api/missions/{mission['id']}/messages", json={"text": "Hello?"})
    assert response.status_code == 202
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert fetched["status"] == "done"
    assert [e["kind"] for e in fetched["events"]][-2:] == ["user_message", "error"]
    assert "did not reach Devin" in fetched["events"][-1]["text"]


def test_reply_to_a_mission_without_a_session_explains_itself(client, devin):
    devin.create_error = DevinUnavailable("down")
    mission = _create(client).get_json()
    response = client.post(f"/api/missions/{mission['id']}/messages", json={"text": "Try again"})
    assert response.status_code == 202
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert fetched["status"] == "failed"
    assert fetched["events"][-1]["kind"] == "error"
    assert devin.sent == []


# ---------- done ----------

def test_mark_done(client):
    mission = _create(client).get_json()
    response = client.post(f"/api/missions/{mission['id']}/done")
    assert response.status_code == 200 and response.get_json() == {}
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "done"
    assert client.post(f"/api/missions/{mission['id']}/done").status_code == 200


def test_mark_done_clears_a_failed_mission(client, devin):
    devin.create_error = DevinUnavailable("down")
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/done")
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "done"


def test_mark_done_unknown_mission_is_404(client):
    assert client.post("/api/missions/m_nope/done").status_code == 404


# ---------- report ----------

REPORT = {"headline": "A leads B", "summary": "It does.", "stats": [{"label": "r", "value": "0.58"}],
          "keyArtifactIds": [], "steps": [{"label": "Read the data", "takeaway": "Messy."}], "caveats": [],
          "nextQuestions": [], "generatedAt": "2026-09-20T12:40:00Z"}


def _deliver(store, mission_id, report=REPORT, status="waiting"):
    row = store.get_mission(mission_id)
    store.apply_sync(mission_id, SyncResult([], [], status, None, report=report, report_settled=True),
                     expected_status=row.status)


def test_request_report(client, devin, store):
    mission = _create(client).get_json()
    store.apply_sync(mission["id"], SyncResult([], [], "waiting", None), expected_status="working")
    response = client.post(f"/api/missions/{mission['id']}/report")
    assert response.status_code == 202 and response.get_json() == {}
    assert devin.sent == [("devin-abc", REPORT_REQUEST)]

    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["reportPending"]) == ("working", True)
    assert "report" not in fetched
    # The request is between the server and Devin: it is not something the user said.
    assert [e["kind"] for e in fetched["events"]] == ["user_message"]


def test_request_report_for_an_unknown_mission_is_404(client, devin):
    response = client.post("/api/missions/m_nope/report")
    assert response.status_code == 404
    assert response.get_json() == {"message": "Mission not found"}
    assert devin.sent == []


def test_request_report_while_one_is_pending_does_nothing(client, devin):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/report")
    before = client.get(f"/api/missions/{mission['id']}").get_json()
    assert client.post(f"/api/missions/{mission['id']}/report").status_code == 202
    assert len(devin.sent) == 1
    assert client.get(f"/api/missions/{mission['id']}").get_json() == before


def test_request_report_without_a_session_explains_itself(client, devin):
    devin.create_error = DevinUnavailable("down")
    mission = _create(client).get_json()
    devin.create_error = None
    response = client.post(f"/api/missions/{mission['id']}/report")
    assert response.status_code == 202 and response.get_json() == {}
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["reportPending"]) == ("failed", False)
    assert [e["kind"] for e in fetched["events"]] == ["user_message", "error", "error"]
    assert "nothing to report on" in fetched["events"][-1]["text"]
    assert devin.sent == []


@pytest.mark.parametrize("was_done", [False, True])
def test_request_report_when_devin_is_down_leaves_the_mission_as_it_was(client, devin, was_done):
    mission = _create(client).get_json()
    if was_done:
        client.post(f"/api/missions/{mission['id']}/done")
    devin.send_error = DevinUnavailable("Devin message failed (503)")
    assert client.post(f"/api/missions/{mission['id']}/report").status_code == 202
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["reportPending"]) == ("done" if was_done else "working", False)
    assert fetched["events"][-1]["kind"] == "error"
    assert "did not reach Devin" in fetched["events"][-1]["text"] and "503" in fetched["events"][-1]["text"]

    devin.send_error = None
    client.post(f"/api/missions/{mission['id']}/report")
    assert client.get(f"/api/missions/{mission['id']}").get_json()["reportPending"] is True


def test_a_delivered_report_is_on_the_mission_but_not_on_summaries(client, store):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/report")
    _deliver(store, mission["id"])
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["report"], fetched["reportPending"], fetched["status"]) == (REPORT, False, "waiting")
    (summary,) = client.get("/api/missions").get_json()
    assert set(summary) == {"id", "title", "hypothesis", "status", "createdAt", "updatedAt"}


def test_regenerating_keeps_showing_the_old_report_while_pending(client, store):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/report")
    _deliver(store, mission["id"])
    client.post(f"/api/missions/{mission['id']}/report")
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["report"], fetched["reportPending"], fetched["status"]) == (REPORT, True, "working")


def test_a_report_for_a_done_mission_reopens_it_only_until_it_arrives(client, store):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/done")
    client.post(f"/api/missions/{mission['id']}/report")
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "working"
    assert [m.id for m in store.live_missions()] == [mission["id"]]
    _deliver(store, mission["id"], status="done")
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "done"


def test_mark_done_while_a_report_is_pending_is_done_at_once_and_still_gets_the_report(client, store):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/report")
    assert client.post(f"/api/missions/{mission['id']}/done").status_code == 200
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["reportPending"]) == ("done", True)
    assert [m.id for m in store.live_missions()] == [mission["id"]]

    _deliver(store, mission["id"], status="done")
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["reportPending"], fetched["report"]) == ("done", False, REPORT)
    assert store.live_missions() == []


def test_a_reply_while_a_report_is_pending_goes_through_and_the_report_is_still_expected(client, devin, store):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/done")
    client.post(f"/api/missions/{mission['id']}/report")
    assert client.post(f"/api/missions/{mission['id']}/messages", json={"text": "One more thing"}).status_code == 202
    assert [text for _, text in devin.sent] == [REPORT_REQUEST, "One more thing"]
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["reportPending"]) == ("working", True)
    # The reply reopened the mission, so the report no longer puts it back to done.
    assert not store.get_mission(mission["id"]).report_restore_done


# ---------- explorer: requesting ----------

def test_request_explorer(client, devin, store, kit):
    mission = _create(client).get_json()
    store.apply_sync(mission["id"], SyncResult([], [], "waiting", None), expected_status="working")
    response = client.post(f"/api/missions/{mission['id']}/explorer")
    assert response.status_code == 202 and response.get_json() == {}

    ((session_id, message),) = devin.sent
    assert session_id == "devin-abc"
    assert message == build_explorer_request(None, {
        "GUIDE.md": "KIT-GUIDE-TEXT", "data.json": '{"rows": [1]}', "index.html": "<!doctype html><title>EXAMPLE-PAGE</title>",
        "kit/kit.css": "body { color: canonical }", "kit/kit.js": "KIT-JS"}, next_version=1)
    assert message.startswith(EXPLORER_OPENING) and "KIT-GUIDE-TEXT" in message and "explorer-v1.zip" in message

    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["explorerPending"], fetched["reportPending"]) == ("working", True, False)
    assert "explorer" not in fetched
    # The request is between the server and Devin: it is not something the user said.
    assert [e["kind"] for e in fetched["events"]] == ["user_message"]


def test_request_explorer_with_instructions_is_a_change_request(client, devin):
    mission = _create(client).get_json()
    response = client.post(f"/api/missions/{mission['id']}/explorer", json={"instructions": "  Add a heatmap  "})
    assert response.status_code == 202
    assert "<instructions>\nAdd a heatmap\n</instructions>" in devin.sent[0][1]
    assert "Add a heatmap" not in repr(client.get(f"/api/missions/{mission['id']}").get_json())


@pytest.mark.parametrize("body", [None, {}, {"instructions": ""}, {"instructions": "  \n "}, {"instructions": None},
                                  {"instructions": 7}, {"instructions": ["Add a heatmap"]}, [1], "text"])
def test_blank_or_malformed_instructions_are_a_plain_build(client, devin, body):
    mission = _create(client).get_json()
    assert client.post(f"/api/missions/{mission['id']}/explorer", json=body).status_code == 202
    assert "<instructions>" not in devin.sent[0][1]
    assert client.get(f"/api/missions/{mission['id']}").get_json()["explorerPending"] is True


def test_instructions_over_the_limit_are_422_and_nothing_is_sent(client, devin):
    mission = _create(client).get_json()
    response = client.post(f"/api/missions/{mission['id']}/explorer", json={"instructions": "x" * 2001})
    assert response.status_code == 422
    assert response.get_json() == {"field": "text", "message": "Keep instructions under 2,000 characters"}
    assert devin.sent == []
    assert client.get(f"/api/missions/{mission['id']}").get_json()["explorerPending"] is False


def test_instructions_at_the_limit_are_accepted_and_padding_does_not_count(client, devin):
    mission = _create(client).get_json()
    response = client.post(f"/api/missions/{mission['id']}/explorer", json={"instructions": f"  {'x' * 2000}\n"})
    assert response.status_code == 202 and "x" * 2000 in devin.sent[0][1]


def test_request_explorer_for_an_unknown_mission_is_404(client, devin):
    response = client.post("/api/missions/m_nope/explorer")
    assert response.status_code == 404
    assert response.get_json() == {"message": "Mission not found"}
    assert devin.sent == []


def test_request_explorer_while_one_is_pending_does_nothing(client, devin):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/explorer")
    before = client.get(f"/api/missions/{mission['id']}").get_json()
    assert client.post(f"/api/missions/{mission['id']}/explorer", json={"instructions": "More"}).status_code == 202
    assert len(devin.sent) == 1
    assert client.get(f"/api/missions/{mission['id']}").get_json() == before


def test_request_explorer_without_a_session_explains_itself(client, devin):
    devin.create_error = DevinUnavailable("down")
    mission = _create(client).get_json()
    devin.create_error = None
    response = client.post(f"/api/missions/{mission['id']}/explorer")
    assert response.status_code == 202 and response.get_json() == {}
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["explorerPending"]) == ("failed", False)
    assert [e["kind"] for e in fetched["events"]] == ["user_message", "error", "error"]
    assert "nothing to explore" in fetched["events"][-1]["text"]
    assert devin.sent == []


@pytest.mark.parametrize("was_done", [False, True])
def test_request_explorer_when_devin_is_down_leaves_the_mission_as_it_was(client, devin, was_done):
    mission = _create(client).get_json()
    if was_done:
        client.post(f"/api/missions/{mission['id']}/done")
    devin.send_error = DevinUnavailable("Devin message failed (503)")
    assert client.post(f"/api/missions/{mission['id']}/explorer").status_code == 202
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["explorerPending"]) == ("done" if was_done else "working", False)
    assert [e["kind"] for e in fetched["events"]] == ["user_message", "error"]
    assert "did not reach Devin" in fetched["events"][-1]["text"] and "503" in fetched["events"][-1]["text"]

    devin.send_error = None
    client.post(f"/api/missions/{mission['id']}/explorer")
    assert client.get(f"/api/missions/{mission['id']}").get_json()["explorerPending"] is True


def test_a_report_and_an_explorer_can_be_pending_together(client, devin):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/report")
    client.post(f"/api/missions/{mission['id']}/explorer")
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["reportPending"], fetched["explorerPending"], fetched["status"]) == (True, True, "working")
    assert len(devin.sent) == 2


# ---------- explorer: on the mission ----------

BUILD = {"version": 2, "title": "Roofs by score", "description": "Click a roof.", "entry": "index.html",
         "builtAt": "2026-09-20T12:40:00Z"}
SITE = {"index.html": b"<!doctype html><script src=kit/kit.js></script>", "data.json": b'{"rows": [1, 2]}',
        "assets/pin.svg": b"<svg xmlns='http://www.w3.org/2000/svg'/>", "assets/map.mjs": b"export default 1",
        "kit/kit.css": b"body { color: from-the-archive }"}


def _site_zip(files=SITE) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _build(store, mission_id, build=BUILD, status="waiting"):
    """What the poller does when a build arrives: unpack it, then record it."""
    unpack(_site_zip(), store.explorer_dir(mission_id, build["version"]), entry=build["entry"])
    row = store.get_mission(mission_id)
    store.apply_sync(mission_id, SyncResult([], [], status, None, explorer=build, explorer_settled=True,
                                            explorer_seen=build["version"]), expected_status=row.status)


@pytest.fixture
def built(client, store):
    mission_id = _create(client).get_json()["id"]
    client.post(f"/api/missions/{mission_id}/explorer")
    _build(store, mission_id)
    return mission_id


def test_a_built_explorer_is_on_the_mission_but_not_on_summaries(client, built):
    fetched = client.get(f"/api/missions/{built}").get_json()
    assert fetched["explorer"] == {"version": 2, "title": "Roofs by score", "description": "Click a roof.",
                                   "src": f"/api/missions/{built}/explorer/2/index.html",
                                   "builtAt": "2026-09-20T12:40:00Z"}
    assert (fetched["explorerPending"], fetched["status"]) == (False, "waiting")
    (summary,) = client.get("/api/missions").get_json()
    assert set(summary) == {"id", "title", "hypothesis", "status", "createdAt", "updatedAt"}


def test_the_src_of_an_unusual_entry_is_url_safe(client, store, built):
    _build_entry = {**BUILD, "version": 3, "entry": "pages/start page.html"}
    row = store.get_mission(built)
    store.request_explorer(built)
    store.apply_sync(built, SyncResult([], [], "waiting", None, explorer=_build_entry, explorer_settled=True),
                     expected_status=row.status)
    src = client.get(f"/api/missions/{built}").get_json()["explorer"]["src"]
    assert src == f"/api/missions/{built}/explorer/3/pages/start%20page.html"


def test_a_change_request_keeps_the_old_build_usable_and_asks_for_the_next_version(client, devin, built):
    client.post(f"/api/missions/{built}/explorer", json={"instructions": "Add a heatmap"})
    fetched = client.get(f"/api/missions/{built}").get_json()
    assert (fetched["explorer"]["version"], fetched["explorerPending"], fetched["status"]) == (2, True, "working")
    assert client.get(fetched["explorer"]["src"]).status_code == 200
    assert "explorer-v3.zip" in devin.sent[-1][1]


def test_an_explorer_for_a_done_mission_reopens_it_only_until_it_arrives(client, store):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/done")
    client.post(f"/api/missions/{mission['id']}/explorer")
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "working"
    assert [m.id for m in store.live_missions()] == [mission["id"]]
    _build(store, mission["id"], status="done")
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "done"
    assert store.live_missions() == []


def test_mark_done_while_a_build_is_pending_is_done_at_once_and_still_gets_the_explorer(client, store):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/explorer")
    assert client.post(f"/api/missions/{mission['id']}/done").status_code == 200
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["explorerPending"]) == ("done", True)
    assert [m.id for m in store.live_missions()] == [mission["id"]]

    _build(store, mission["id"], status="done")
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["explorerPending"], fetched["explorer"]["version"]) == ("done", False, 2)
    assert store.live_missions() == []


def test_a_reply_while_a_build_is_pending_goes_through_and_the_build_is_still_expected(client, devin, store):
    mission = _create(client).get_json()
    client.post(f"/api/missions/{mission['id']}/done")
    client.post(f"/api/missions/{mission['id']}/explorer")
    assert client.post(f"/api/missions/{mission['id']}/messages", json={"text": "One more thing"}).status_code == 202
    assert devin.sent[-1][1] == "One more thing" and len(devin.sent) == 2
    fetched = client.get(f"/api/missions/{mission['id']}").get_json()
    assert (fetched["status"], fetched["explorerPending"]) == ("working", True)
    # The reply reopened the mission, so the build no longer puts it back to done.
    assert not store.get_mission(mission["id"]).explorer_restore_done
    _build(store, mission["id"], status="waiting")
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "waiting"


# ---------- explorer: serving ----------

def test_the_entry_is_served_sandboxed(client, built):
    response = client.get(f"/api/missions/{built}/explorer/2/index.html?theme=dark")
    assert response.status_code == 200
    assert response.data == SITE["index.html"]
    assert response.content_type == "text/html; charset=utf-8"
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"] == explorer_csp("http://localhost")


def test_the_policy_names_the_servers_own_origin_because_self_matches_nothing_when_sandboxed():
    """A document sandboxed without allow-same-origin has an opaque origin, and Chrome then matches
    'self' against nothing, which would block the explorer's own kit and data files."""
    policy = explorer_csp("http://localhost:5173")
    assert policy == (
        "sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; "
        "default-src http://localhost:5173 data: blob:; "
        "script-src http://localhost:5173 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src http://localhost:5173 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net "
        "https://fonts.googleapis.com; font-src http://localhost:5173 data: https://fonts.gstatic.com; "
        "img-src * data: blob:; connect-src *; worker-src blob:; child-src blob:")
    assert "'self'" not in policy and "allow-same-origin" not in policy


def test_the_policy_follows_the_host_the_browser_used(client, built):
    response = client.get(f"/api/missions/{built}/explorer/2/index.html", headers={"Host": "127.0.0.1:8030"})
    assert "script-src http://127.0.0.1:8030 " in response.headers["Content-Security-Policy"]


@pytest.mark.parametrize("host", ["evil.test; script-src *", "a b", "x'y", "h\\st", ""])
def test_a_malformed_host_never_reaches_the_policy(client, built, host):
    response = client.get(f"/api/missions/{built}/explorer/2/index.html", headers={"Host": host})
    policy = response.headers.get("Content-Security-Policy", "")
    assert response.status_code in (200, 400)
    assert "script-src *" not in policy and "evil.test;" not in policy
    if response.status_code == 200:
        assert policy.startswith("sandbox allow-scripts ")


@pytest.mark.parametrize("path, content_type, sandboxed", [
    ("data.json", "application/json", False),
    ("assets/map.mjs", "text/javascript; charset=utf-8", False),
    ("assets/pin.svg", "image/svg+xml; charset=utf-8", True),
])
def test_other_files_are_served_with_the_same_headers_and_no_policy_unless_they_are_documents(
        client, built, path, content_type, sandboxed):
    response = client.get(f"/api/missions/{built}/explorer/2/{path}")
    assert (response.status_code, response.data, response.content_type) == (200, SITE[path], content_type)
    assert (response.headers["Access-Control-Allow-Origin"], response.headers["X-Content-Type-Options"],
            response.headers["Cache-Control"]) == ("*", "nosniff", "no-store")
    assert ("Content-Security-Policy" in response.headers) is sandboxed


def test_a_repeat_request_is_never_answered_from_a_cache(client, built):
    first = client.get(f"/api/missions/{built}/explorer/2/data.json")
    again = client.get(f"/api/missions/{built}/explorer/2/data.json", headers={
        "If-None-Match": first.headers.get("ETag", "x"), "If-Modified-Since": first.headers.get("Last-Modified", "x")})
    assert (again.status_code, again.data) == (200, SITE["data.json"])


def test_kit_paths_serve_the_canonical_kit_not_the_archives_copy(client, built, store, kit):
    response = client.get(f"/api/missions/{built}/explorer/2/kit/kit.css")
    assert (response.status_code, response.data) == (200, b"body { color: canonical }")
    assert response.content_type == "text/css; charset=utf-8"
    assert response.headers["Access-Control-Allow-Origin"] == "*" and response.headers["Cache-Control"] == "no-store"
    assert not (store.explorer_dir(built, 2) / "kit").exists()

    # A design fix reaches explorers that were built before it.
    (kit / "kit.css").write_text("body { color: fixed }")
    assert client.get(f"/api/missions/{built}/explorer/2/kit/kit.css").data == b"body { color: fixed }"
    assert client.get(f"/api/missions/{built}/explorer/2/kit/kit.js").data == b"KIT-JS"


@pytest.mark.parametrize("path", [
    "kit/GUIDE.md", "kit/index.html", "kit/data.json", "kit/nope.css", "kit/", "kit", "kit/../index.html",
    "kit/../../k.db", "kit/%2e%2e/GUIDE.md",
])
def test_kit_paths_outside_the_kits_own_files_are_404(client, built, path):
    assert client.get(f"/api/missions/{built}/explorer/2/{path}").status_code == 404


def test_the_kit_is_only_served_under_a_build_that_exists(client, built):
    assert client.get(f"/api/missions/{built}/explorer/9/kit/kit.css").status_code == 404
    assert client.get("/api/missions/m_nope/explorer/2/kit/kit.css").status_code == 404


@pytest.mark.parametrize("url", [
    "/api/missions/m_nope/explorer/2/index.html",
    "/api/missions/{id}/explorer/1/index.html",
    "/api/missions/{id}/explorer/3/index.html",
    "/api/missions/{id}/explorer/0/index.html",
    "/api/missions/{id}/explorer/-2/index.html",
    "/api/missions/{id}/explorer/two/index.html",
    "/api/missions/{id}/explorer/2.0/index.html",
    "/api/missions/{id}/explorer/2/",
    "/api/missions/{id}/explorer/2",
    "/api/missions/{id}/explorer/2/missing.html",
    "/api/missions/{id}/explorer/2/assets",
    "/api/missions/{id}/explorer/2/assets/",
    "/api/missions/{id}/explorer/2/INDEX.HTM",
])
def test_unknown_missions_versions_and_paths_are_404(client, built, url):
    response = client.get(url.format(id=built))
    assert response.status_code == 404
    assert "message" in response.get_json()


@pytest.mark.parametrize("path", [
    "../2/index.html", "../../../k.db", "..%2F..%2F..%2Fk.db", "%2e%2e/%2e%2e/%2e%2e/k.db", "assets/../../../../k.db",
    "assets/../index.html", "/etc/passwd", "%2Fetc%2Fpasswd", "//etc/passwd", "..\\..\\k.db", "assets\\pin.svg",
    "....//....//k.db", "index.html%00.png", "./index.html",
])
def test_path_traversal_is_404(client, built, store, tmp_path, path):
    assert (tmp_path / "k.db").is_file()
    # Doubled slashes are first redirected to the tidied URL, which is then judged like any other.
    response = client.get(f"/api/missions/{built}/explorer/2/{path}", follow_redirects=True)
    assert response.status_code == 404
    assert b"SQLite" not in response.data


def test_a_file_outside_the_allowlist_is_not_served_even_if_it_is_on_disk(client, built, store):
    (store.explorer_dir(built, 2) / "notes.md").write_text("left by hand")
    assert client.get(f"/api/missions/{built}/explorer/2/notes.md").status_code == 404


def test_a_link_out_of_the_build_is_not_followed(client, built, store, tmp_path):
    (store.explorer_dir(built, 2) / "link.html").symlink_to(tmp_path / "k.db")
    (store.explorer_dir(built, 2) / "inside.html").symlink_to(store.explorer_dir(built, 2) / "index.html")
    assert client.get(f"/api/missions/{built}/explorer/2/link.html").status_code == 404
    assert client.get(f"/api/missions/{built}/explorer/2/inside.html").status_code == 200


def test_another_missions_build_is_not_reachable_through_this_one(client, built):
    other = _create(client).get_json()["id"]
    assert client.get(f"/api/missions/{other}/explorer/2/index.html").status_code == 404
    assert client.get(f"/api/missions/{other}/explorer/2/../../{built}/2/index.html").status_code == 404


def test_older_versions_stay_served(client, store, built):
    store.request_explorer(built)
    _build(store, built, {**BUILD, "version": 3})
    assert client.get(f"/api/missions/{built}").get_json()["explorer"]["src"].endswith("/explorer/3/index.html")
    assert client.get(f"/api/missions/{built}/explorer/2/index.html").status_code == 200
    assert client.get(f"/api/missions/{built}/explorer/3/index.html").status_code == 200


def test_explorer_404s_carry_the_cors_header_too_and_other_routes_never_do(client, built):
    missing = client.get(f"/api/missions/{built}/explorer/2/missing.json")
    assert (missing.status_code, missing.headers["Access-Control-Allow-Origin"]) == (404, "*")
    for url in ("/api/meta", f"/api/missions/{built}", f"/api/missions/{built}/attachments/plot.png"):
        assert "Access-Control-Allow-Origin" not in client.get(url).headers


def test_explorer_files_are_read_only(client, built):
    for method in (client.post, client.put, client.delete):
        assert method(f"/api/missions/{built}/explorer/2/index.html").status_code == 405


# ---------- attachments ----------

def test_attachment_proxy_serves_images(client):
    mission = _create(client).get_json()
    response = client.get(f"/api/missions/{mission['id']}/attachments/plot.png")
    assert response.status_code == 200
    assert response.data == b"PNGDATA"
    assert response.content_type == "image/png"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_attachment_proxy_handles_encoded_names(client, devin):
    devin.attachments = [Attachment("tile 1.png", "https://files.test/t1")]
    devin.downloads["tile 1.png"] = (b"T1", "image/png")
    mission = _create(client).get_json()
    assert client.get(f"/api/missions/{mission['id']}/attachments/tile%201.png").data == b"T1"


def test_attachment_proxy_refuses_unknown_names(client, devin):
    mission = _create(client).get_json()
    response = client.get(f"/api/missions/{mission['id']}/attachments/secrets.png")
    assert response.status_code == 404
    assert response.get_json() == {"message": "Attachment not found"}


@pytest.mark.parametrize("failure", [AttachmentRejected("attachment is not an image (text/html)"),
                                     AttachmentRejected("attachment is larger than 10 MB")])
def test_attachment_proxy_refuses_what_the_client_rejects(client, devin, failure):
    devin.downloads["plot.png"] = failure
    mission = _create(client).get_json()
    assert client.get(f"/api/missions/{mission['id']}/attachments/plot.png").status_code == 404


def test_attachment_proxy_when_devin_is_down(client, devin):
    mission = _create(client).get_json()
    devin.attachments_error = DevinUnavailable("503")
    assert client.get(f"/api/missions/{mission['id']}/attachments/plot.png").status_code == 404


def test_attachment_proxy_unknown_mission_or_no_session(client, devin):
    assert client.get("/api/missions/m_nope/attachments/plot.png").status_code == 404
    devin.create_error = DevinUnavailable("down")
    mission = _create(client).get_json()
    assert client.get(f"/api/missions/{mission['id']}/attachments/plot.png").status_code == 404


# ---------- datasets ----------

def test_list_datasets_is_seeded(client):
    datasets = client.get("/api/datasets").get_json()
    assert [d["id"] for d in datasets] == ["pudl", "sentinel-2", "global-water-watch", "viirs", "openstreetmap", "open-meteo"]


def test_link_dataset(client):
    response = client.post("/api/datasets", json={"name": " County outages ", "url": " https://x.test/o.csv "})
    assert response.status_code == 201
    dataset = response.get_json()
    assert (dataset["name"], dataset["url"], dataset["kind"]) == ("County outages", "https://x.test/o.csv", "other")
    assert client.get("/api/datasets").get_json()[0] == dataset


@pytest.mark.parametrize("body, field, message", [
    ({"url": "https://x.test"}, "name", "Enter a name"),
    ({"name": "  ", "url": "https://x.test"}, "name", "Enter a name"),
    ({"name": 5, "url": "https://x.test"}, "name", "Enter a name"),
    ({"name": "", "url": "nope"}, "name", "Enter a name"),
    ({"name": "X"}, "url", "Enter an http or https URL"),
    ({"name": "X", "url": ""}, "url", "Enter an http or https URL"),
    ({"name": "X", "url": "ftp://x.test"}, "url", "Enter an http or https URL"),
    ({"name": "X", "url": "javascript:alert(1)"}, "url", "Enter an http or https URL"),
    ({"name": "X", "url": "https://"}, "url", "Enter an http or https URL"),
    ({"name": "X", "url": "x.test/data"}, "url", "Enter an http or https URL"),
])
def test_link_dataset_validation(client, body, field, message):
    response = client.post("/api/datasets", json=body)
    assert response.status_code == 422
    assert response.get_json() == {"field": field, "message": message}
    assert len(client.get("/api/datasets").get_json()) == 6


def test_http_urls_are_accepted(client):
    assert client.post("/api/datasets", json={"name": "X", "url": "http://x.test"}).status_code == 201


# ---------- misc ----------

def test_unknown_api_route_is_json_404(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert "message" in response.get_json()


def test_wrong_method_is_json_405(client):
    response = client.delete("/api/missions")
    assert response.status_code == 405
    assert "message" in response.get_json()


def test_no_cors_headers(client):
    assert "Access-Control-Allow-Origin" not in client.get("/api/meta").headers


def test_end_to_end_with_the_fake_and_the_poller(store):
    clock = [1_800_000_000.0]
    fake = FakeDevin(clock=lambda: clock[0], beat_seconds=3.0)
    client = create_app(store, fake, demo=True).test_client()
    poller = Poller(store, fake)

    mission = _create(client).get_json()
    assert "sessionUrl" not in mission
    for _ in range(12):
        poller.tick()
        clock[0] += 5
    waiting = client.get(f"/api/missions/{mission['id']}").get_json()
    assert waiting["status"] == "waiting"
    assert {e["artifact"]["type"] for e in waiting["events"] if e["kind"] == "artifact"} == {
        "chart", "images", "relation", "table", "stats", "image"}

    client.post(f"/api/missions/{mission['id']}/messages", json={"text": "What about the outlier?"})
    assert client.get(f"/api/missions/{mission['id']}").get_json()["status"] == "working"
    for _ in range(4):
        poller.tick()
        clock[0] += 5
    replied = client.get(f"/api/missions/{mission['id']}").get_json()
    assert replied["status"] == "waiting"
    assert len(replied["events"]) == len(waiting["events"]) + 4
    assert [e["text"] for e in replied["events"] if e["kind"] == "user_message"] == [
        HYPOTHESIS, "What about the outlier?"]

    client.post(f"/api/missions/{mission['id']}/done")
    assert client.get("/api/missions").get_json()[0]["status"] == "done"


def _tick(poller, clock, times):
    for _ in range(times):
        poller.tick()
        clock[0] += 5


def test_report_end_to_end_with_the_fake_and_the_poller(store):
    clock = [1_800_000_000.0]
    fake = FakeDevin(clock=lambda: clock[0], beat_seconds=3.0)
    client = create_app(store, fake, demo=True).test_client()
    poller = Poller(store, fake)
    mission_id = _create(client).get_json()["id"]
    _tick(poller, clock, 12)
    before = client.get(f"/api/missions/{mission_id}").get_json()
    assert (before["status"], before["reportPending"]) == ("waiting", False)

    client.post(f"/api/missions/{mission_id}/report")
    poller.tick()
    pending = client.get(f"/api/missions/{mission_id}").get_json()
    assert (pending["status"], pending["reportPending"], "report" in pending) == ("working", True, False)
    assert pending["events"] == before["events"]

    clock[0] += 5
    _tick(poller, clock, 2)
    first = client.get(f"/api/missions/{mission_id}").get_json()
    assert (first["status"], first["reportPending"]) == ("waiting", False)
    assert [e["kind"] for e in first["events"]][-3:] == ["thought", "conclusion", "report"]
    assert first["events"][-3]["text"] == "The report is ready."
    assert REPORT_REQUEST not in repr(first["events"])
    artifacts = {e["artifact"]["id"]: e["artifact"] for e in first["events"] if e["kind"] == "artifact"}
    assert [artifacts[i]["type"] for i in first["report"]["keyArtifactIds"]] == ["chart", "relation", "stats"]
    assert set(first["report"]) == {"headline", "summary", "stats", "keyArtifactIds", "steps", "caveats",
                                    "nextQuestions", "generatedAt"}

    # Regenerating from a done mission: a different report, one marker, and back to done.
    client.post(f"/api/missions/{mission_id}/done")
    client.post(f"/api/missions/{mission_id}/report")
    assert client.get(f"/api/missions/{mission_id}").get_json()["status"] == "working"
    clock[0] += 5
    _tick(poller, clock, 2)
    second = client.get(f"/api/missions/{mission_id}").get_json()
    assert (second["status"], second["reportPending"]) == ("done", False)
    assert second["report"]["summary"] != first["report"]["summary"]
    assert [e["kind"] for e in second["events"]].count("report") == 1
    assert [e["kind"] for e in second["events"]][-2:] == ["conclusion", "report"]


def test_explorer_end_to_end_with_the_fake_and_the_poller(store, kit):
    clock = [1_800_000_000.0]
    fake = FakeDevin(clock=lambda: clock[0], beat_seconds=3.0, kit_dir=kit)
    client = create_app(store, fake, demo=True, kit_dir=kit).test_client()
    poller = Poller(store, fake)
    mission_id = _create(client).get_json()["id"]
    _tick(poller, clock, 12)
    before = client.get(f"/api/missions/{mission_id}").get_json()
    assert (before["status"], before["explorerPending"], "explorer" in before) == ("waiting", False, False)

    client.post(f"/api/missions/{mission_id}/explorer")
    poller.tick()
    pending = client.get(f"/api/missions/{mission_id}").get_json()
    assert (pending["status"], pending["explorerPending"], "explorer" in pending) == ("working", True, False)
    assert pending["events"] == before["events"]

    clock[0] += 5
    _tick(poller, clock, 2)
    first = client.get(f"/api/missions/{mission_id}").get_json()
    assert (first["status"], first["explorerPending"]) == ("waiting", False)
    assert [e["kind"] for e in first["events"]][-3:] == ["thought", "conclusion", "explorer"]
    assert first["events"][-3]["text"] == "The explorer is ready."
    # Neither the request nor the kit inside it ever shows in the thread.
    assert EXPLORER_OPENING not in repr(first["events"]) and "KIT-GUIDE-TEXT" not in repr(first["events"])
    assert set(first["explorer"]) == {"version", "title", "description", "src", "builtAt"}
    assert (first["explorer"]["version"], first["explorer"]["src"]) == (
        1, f"/api/missions/{mission_id}/explorer/1/index.html")

    page = client.get(first["explorer"]["src"])
    assert (page.status_code, page.data) == (200, b"<!doctype html><title>EXAMPLE-PAGE</title>")
    assert client.get(f"/api/missions/{mission_id}/explorer/1/data.json").get_json() == {"rows": [1]}
    assert client.get(f"/api/missions/{mission_id}/explorer/1/kit/kit.css").data == b"body { color: canonical }"
    assert not (store.explorer_dir(mission_id, 1) / "kit").exists()

    # A report and a change request from a done mission: both land, in order, and it goes back to done.
    client.post(f"/api/missions/{mission_id}/done")
    client.post(f"/api/missions/{mission_id}/report")
    client.post(f"/api/missions/{mission_id}/explorer", json={"instructions": "Add a heatmap"})
    assert client.get(f"/api/missions/{mission_id}").get_json()["status"] == "working"
    clock[0] += 5
    _tick(poller, clock, 2)
    second = client.get(f"/api/missions/{mission_id}").get_json()
    assert (second["status"], second["explorerPending"], second["reportPending"]) == ("done", False, False)
    assert second["explorer"]["version"] == 2 and "Add a heatmap" in second["explorer"]["description"]
    assert second["explorer"]["src"].endswith("/explorer/2/index.html")
    kinds = [e["kind"] for e in second["events"]]
    assert kinds[-3:] == ["conclusion", "report", "explorer"]
    assert (kinds.count("report"), kinds.count("explorer"), kinds.count("error")) == (1, 1, 0)
    assert client.get(first["explorer"]["src"]).status_code == 200
    assert store.live_missions() == []

    before = client.get(f"/api/missions/{mission_id}").get_json()
    _tick(poller, clock, 2)
    assert client.get(f"/api/missions/{mission_id}").get_json() == before


def test_behind_a_proxy_the_policy_names_the_address_the_browser_used(client, built):
    """The Vite dev proxy (and any reverse proxy) rewrites Host to the backend's own address."""
    response = client.get(
        f"/api/missions/{built}/explorer/2/index.html",
        headers={"Host": "127.0.0.1:8030", "X-Forwarded-Host": "localhost:5173", "X-Forwarded-Proto": "http"})
    policy = response.headers["Content-Security-Policy"]
    assert "script-src http://localhost:5173 " in policy and "127.0.0.1:8030" not in policy


def test_a_forwarded_https_host_is_honoured(client, built):
    response = client.get(
        f"/api/missions/{built}/explorer/2/index.html",
        headers={"X-Forwarded-Host": "kingdom.example", "X-Forwarded-Proto": "https"})
    assert "script-src https://kingdom.example " in response.headers["Content-Security-Policy"]


@pytest.mark.parametrize("forwarded", ["evil.test; script-src *", "a, b", "x y"])
def test_a_malformed_forwarded_host_falls_back_to_the_real_one(client, built, forwarded):
    response = client.get(f"/api/missions/{built}/explorer/2/index.html", headers={"X-Forwarded-Host": forwarded})
    policy = response.headers["Content-Security-Policy"]
    assert "script-src http://localhost " in policy and "evil.test" not in policy
