from server.app import create_app
from server.devin import FakeDevin
from server.store import Store
from server.sync import SyncResult


def test_pin_and_rename_persist_and_devin_cannot_replace_the_name(tmp_path):
    path = tmp_path / "missions.db"
    store = Store(path)
    app = create_app(store, FakeDevin(), demo=True).test_client()
    mission = app.post("/api/missions", json={"hypothesis": "A research question"}).get_json()
    url = f"/api/missions/{mission['id']}"
    assert app.post(url + "/settings", json={"title": "  Best result  ", "pinned": True}).status_code == 200
    store.apply_sync(mission['id'], SyncResult([], [], "working", None, title="Devin's title"), expected_status="working")
    reopened = create_app(Store(path), FakeDevin(), demo=True).test_client()
    summary = reopened.get("/api/missions").get_json()[0]
    assert summary["title"] == "Best result" and summary["pinned"] is True
    assert reopened.get(url).get_json()["title"] == "Best result"
    assert reopened.post(url + "/settings", json={"pinned": False}).status_code == 200
    assert not reopened.get(url).get_json().get("pinned", False)


def test_delete_removes_mission_from_views_and_polling_without_destroying_its_history(tmp_path):
    store = Store(tmp_path / "missions.db")
    app = create_app(store, FakeDevin(), demo=True).test_client()
    mission = app.post("/api/missions", json={"hypothesis": "A research question"}).get_json()
    url = f"/api/missions/{mission['id']}"
    store.request_report(mission['id'])
    assert app.post(url + "/delete").status_code == 200
    assert app.get(url).status_code == 404
    assert app.get("/api/missions").get_json() == []
    assert store.live_missions() == []
    assert store.list_events(mission['id'])
    assert not store.apply_sync(mission['id'], SyncResult([], [], "working", None), expected_status="working")
    assert app.post(url + "/messages", json={"text": "Continue"}).status_code == 404


def test_invalid_settings_do_not_change_the_mission(tmp_path):
    store = Store(tmp_path / "missions.db")
    app = create_app(store, FakeDevin(), demo=True).test_client()
    mission = app.post("/api/missions", json={"hypothesis": "A research question"}).get_json()
    url = f"/api/missions/{mission['id']}"
    for body in ({"title": " "}, {"title": "x" * 81}, {"pinned": "true"}, {"pinned": None}):
        assert app.post(url + "/settings", json=body).status_code == 422
    assert app.get(url).get_json()["title"] == mission["title"]
    assert app.post("/api/missions/m_missing/settings", json={"pinned": True}).status_code == 404
