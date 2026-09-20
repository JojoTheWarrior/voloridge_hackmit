import json

from warsignal.ai import brain
from warsignal.ai.devin_client import DevinBrain
from warsignal.mission import publish
from warsignal.mission.model import MissionPlan, MissionResult


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


def test_devin_json_happy_path(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "warsignal.ai.devin_client.requests.post",
        lambda *args, **kwargs: (
            calls.append(("post", args, kwargs)) or
            _Response(200, {"session_id": "s1", "url": "https://app.devin.ai/sessions/s1"})
        ),
    )
    polls = iter([
        _Response(200, {"status_enum": "working", "structured_output": None}),
        _Response(
            200,
            {
                "status_enum": "finished",
                "url": "https://app.devin.ai/sessions/s1",
                "structured_output": {"answer": "ok"},
            },
        ),
    ])
    monkeypatch.setattr("warsignal.ai.devin_client.requests.get", lambda *args, **kwargs: next(polls))
    monkeypatch.setattr("warsignal.ai.devin_client.time.sleep", lambda _: None)
    result = DevinBrain("secret").ask_json(
        "system",
        "user",
        {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]},
        title="WarSignal planner · M1",
        tags=["warsignal", "purpose:planner", "mission:M1"],
        timeout_s=1,
        poll_s=0,
    )
    assert result["answer"] == "ok"
    assert result["_meta"]["session_url"].endswith("/s1")
    assert calls[0][2]["json"]["title"] == "WarSignal planner · M1"
    assert calls[0][2]["json"]["tags"][0] == "warsignal"


def test_devin_falls_back_to_openai(monkeypatch):
    monkeypatch.setenv("DEVIN_API_KEY", "secret")
    monkeypatch.setenv("WARSIGNAL_BRAIN", "devin")
    monkeypatch.setattr(
        "warsignal.ai.devin_client.requests.post",
        lambda *args, **kwargs: _Response(403, {"detail": "Unauthorized"}),
    )
    monkeypatch.setattr(
        brain,
        "chat_json",
        lambda *args, **kwargs: {"indicator_a": "a", "_meta": {"model": "test"}},
    )
    result = brain.think_json(
        "system",
        "user",
        {"type": "object", "properties": {"indicator_a": {"type": "string"}}},
        purpose="planner",
        mission_id="M1",
    )
    assert result["indicator_a"] == "a"
    assert result["_meta"]["backend"] == "openai"
    assert result["_meta"]["session_url"] is None


def test_manifest_records_brain_sessions(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setattr(publish, "RUNS", runs)
    monkeypatch.setattr(publish, "LOCK", runs / ".lock")
    result = MissionResult(
        "M1",
        "now",
        "hypothesis",
        MissionPlan("finance.BZ=F.close", "finance.^GSPC.close"),
        brain_sessions=[
            {
                "purpose": "planner",
                "backend": "devin",
                "session_url": "https://app.devin.ai/sessions/s1",
            }
        ],
    )
    folder = publish.write_run_folder(result, judge={})
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest["brain_sessions"][0]["backend"] == "devin"
    assert result.to_row()["brain_sessions"].endswith("/s1")
