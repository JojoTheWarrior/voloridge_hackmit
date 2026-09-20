import json
import sys

from warsignal.ai.devin_client import BrainUnavailable
from warsignal.mission import detach


class _Response:
    status_code = 200
    text = ""

    def json(self):
        return {"session_id": "devin-x", "url": "https://app.devin.ai/sessions/x"}


def test_spawn_mission_agent_creates_session_and_status(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setenv("DEVIN_API_KEY", "test-key")
    monkeypatch.setattr(detach, "STATUS_DIR", tmp_path / "status")
    monkeypatch.setattr(
        "warsignal.ai.devin_client.requests.post",
        lambda url, **kwargs: (calls.append((url, kwargs)) or _Response()),
    )
    session_id, url = detach.spawn_mission_agent("Iran news leads Brent", brain_backend="heuristic")
    assert session_id == "devin-x"
    assert url.endswith("/x")
    body = calls[0][1]["json"]
    assert body["title"].startswith("Mission M")
    assert body["tags"][0] == "warsignal"
    assert "Iran news leads Brent" in body["prompt"]
    mission_id = next(tag.split(":", 1)[1] for tag in body["tags"] if tag.startswith("mission:"))
    status = json.loads((tmp_path / "status" / f"{mission_id}.json").read_text())
    assert status["state"] == "queued"
    assert status["agent_session_url"] == url


def test_main_detach_does_not_import_runner(monkeypatch, capsys):
    import main

    monkeypatch.setattr(
        "warsignal.mission.detach.spawn_mission_agent",
        lambda hypothesis, **kwargs: ("devin-x", "https://app.devin.ai/sessions/x"),
    )
    monkeypatch.setattr(sys, "argv", ["main.py", "mission", "test", "--detach"])
    sys.modules.pop("warsignal.mission.runner", None)
    main.main()
    assert "mission started: https://app.devin.ai/sessions/x" in capsys.readouterr().out
    assert "warsignal.mission.runner" not in sys.modules
