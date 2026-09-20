from warsignal.ui.app import create_app


def test_ui_routes():
    client = create_app().test_client()
    assert client.get("/").status_code == 200
    response = client.get("/api/indicators")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
