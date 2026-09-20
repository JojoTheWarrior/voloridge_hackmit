from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from warsignal.ai.devin_client import DevinBrain
from .ids import new_mission_id


ROOT = Path(__file__).resolve().parents[2]
STATUS_DIR = ROOT / "missions" / "status"


def _write_status(mission_id, payload):
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    target = STATUS_DIR / f"{mission_id}.json"
    fd, temporary = tempfile.mkstemp(prefix=f".{mission_id}.", dir=STATUS_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def spawn_mission_agent(hypothesis: str, *, brain_backend: str | None = None, max_acu: int = 10):
    mission_id = new_mission_id()
    escaped_hypothesis = hypothesis.replace("\\", "\\\\").replace('"', '\\"')
    brain_flag = f" --brain {brain_backend}" if brain_backend else ""
    prompt = (
        "You are a WarSignal mission agent. Clone "
        "https://github.com/JojoTheWarrior/voloridge_hackmit (branch main), "
        "`pip install -r requirements.txt`, then run `python main.py fetch --quick` "
        "if data/cache is missing. Read missions/status/SCHEMA.md. "
        f"Mission id: {mission_id}. Hypothesis: {hypothesis}. "
        "Steps: (1) write "
        f"missions/status/{mission_id}.json with state=running, stage=planning, "
        "progress=0.05, agent_session_url=<your session url>, commit+push to main "
        "(`git pull --rebase --autostash` before every push, never force-push); "
        "(2) run "
        f'`python main.py mission "{escaped_hypothesis}" --viz --publish{brain_flag}`; '
        "update the status file at least at stages loading/stats/judging/narrative/"
        "viz/publishing (progress monotone, signal from stats if available, message = "
        "one line) and push each time; (3) when done set state=done (or failed with "
        "message), stage=done, progress=1.0, run_folder, scores from the run's "
        "judge.json, finished_at, and push. Never commit .env or API keys. "
        "Provide structured output {mission_id, state, run_folder, session_url} and stop. "
        "API keys: use the DEVIN_API_KEY/OPENAI_API_KEY/TYPESAFE_API_KEY secrets "
        "provisioned in your environment if present; otherwise run with "
        "`--brain heuristic` and note it in the status message."
    )
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "mission_id": {"type": "string"},
            "state": {"type": "string"},
            "run_folder": {"type": ["string", "null"]},
            "session_url": {"type": "string"},
        },
        "required": ["mission_id", "state", "run_folder", "session_url"],
        "additionalProperties": False,
    }
    session_id, session_url = DevinBrain().create_session(
        prompt,
        title=f"Mission {mission_id}",
        tags=["warsignal", "mission-agent", f"mission:{mission_id}"],
        schema=schema,
        max_acu=max_acu,
    )
    now = datetime.now(timezone.utc).isoformat()
    _write_status(
        mission_id,
        {
            "mission_id": mission_id,
            "hypothesis": hypothesis,
            "state": "queued",
            "stage": "queued",
            "progress": 0,
            "agent_session_url": session_url,
            "started_at": now,
            "updated_at": now,
        },
    )
    return session_id, session_url
