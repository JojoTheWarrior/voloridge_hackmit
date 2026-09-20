from server.app import create_app
from server.artifacts import normalise_artifact
from server.devin import Attachment, SessionSnapshot
from server.store import Store


SOURCE = "https://app.devin.ai/attachments/owned-id/image%201.png"
ARTIFACT = {"id": "a1", "type": "images", "title": "Evidence", "items": [{"src": SOURCE}]}


def test_new_artifacts_route_private_links_through_kingdom():
    artifact = normalise_artifact(ARTIFACT, mission_id="m_test")
    assert artifact["items"][0]["src"] == "/api/missions/m_test/attachments/image%201.png"


def test_existing_reports_and_unlisted_screenshots_are_served_from_their_own_session(tmp_path):
    store = Store(tmp_path / "k.db")
    mission = store.create_mission("Question", title="Result", dataset_ids=[], reference=None, prompt="Question")
    store.set_session(mission.id, "session-id", None)
    store.append_event(mission.id, "artifact", {"artifact": ARTIFACT})
    store.mark_done(mission.id)

    class Images:
        def list_attachments(self, session_id):
            assert session_id == "session-id"
            return []  # Devin sometimes leaves screenshots out of this listing.

        def get_session(self, session_id):
            return SessionSnapshot("finished", None, {"artifacts": [ARTIFACT]})

        def download(self, attachment):
            assert attachment == Attachment("image 1.png", SOURCE)
            return b"verified-image-bytes", "image/png"

    client = create_app(store, Images(), demo=False).test_client()
    url = f"/api/missions/{mission.id}"
    source = client.get(url).get_json()["events"][0]["artifact"]["items"][0]["src"]
    response = client.get(source)
    assert response.status_code == 200 and response.data == b"verified-image-bytes"
    assert response.mimetype == "image/png"
    assert client.get(url + "/attachments/not-in-this-mission.png").status_code == 404
    # Newly normalized stored events no longer contain the original URL; the session still does.
    newer = store.create_mission("Q", title="New", dataset_ids=[], reference=None, prompt="Q")
    store.set_session(newer.id, "session-id", None)
    store.append_event(newer.id, "artifact", {"artifact": normalise_artifact(ARTIFACT, mission_id=newer.id)})
    assert client.get(f"/api/missions/{newer.id}/attachments/image%201.png").status_code == 200
