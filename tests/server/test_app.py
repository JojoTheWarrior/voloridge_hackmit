"""Tests for server.app: every route, with a scripted Devin and a real SQLite store."""
from __future__ import annotations

import pytest

from server.app import create_app
from server.devin import Attachment, AttachmentRejected, DevinUnavailable, FakeDevin, SessionRef
from server.poller import Poller
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
def client(store, devin):
    return create_app(store, devin, demo=False).test_client()


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
                            "sessionUrl", "events"}
    assert mission["id"].startswith("m_")
    assert mission["title"] == "Do satellite images of storm damage predict how"
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
    assert [d["id"] for d in datasets] == ["gdelt", "yahoo", "open-meteo", "cams"]


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
    assert len(client.get("/api/datasets").get_json()) == 4


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
