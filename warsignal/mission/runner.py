from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from warsignal.ai.jev_client import JevClient
from warsignal.ai.prompts import JEV_QUESTIONS, NARRATIVE_SYSTEM
from warsignal.ai.openai_client import chat_text
from warsignal.analysis.stats import run_all
from warsignal.config import DATA_RAW, START, END
from warsignal.indicators import get_series
from .model import MissionResult
from .planner import plan_mission

ROOT = Path(__file__).resolve().parents[2]


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _narrative(hypothesis, plan, stats, use_ai):
    if use_ai:
        try:
            return chat_text(NARRATIVE_SYSTEM, json.dumps({"hypothesis": hypothesis, "plan": plan.__dict__, "stats": stats}),
                             model=__import__("warsignal.config", fromlist=["env"]).env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"))[0]
        except Exception:
            pass
    corr = (stats.get("correlation") or {}).get("pearson_r")
    return (f"**Verdict:** {'supported' if stats.get('sign_matches_expectation') else 'not supported'} "
            f"(Pearson r={corr!s}, n={stats.get('n_obs', 0)}).\n\n"
            f"The best tested lag was {(stats.get('lagged') or {}).get('best_lag')} days with "
            f"r={(stats.get('lagged') or {}).get('best_r')}.\n\n"
            "This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.")


def run_mission(hypothesis, mission_id=None, use_ai=True, viz=False):
    mission_id = mission_id or f"M{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3)}"
    created = datetime.now(timezone.utc).isoformat()
    try:
        plan, planner_model = plan_mission(hypothesis)
        a = get_series(plan.indicator_a, START, END)
        b = get_series(plan.indicator_b, START, END)
        from warsignal.indicators.events import load_timeline
        stats = run_all(plan, a, b, load_timeline())
        judge = JevClient().judge({**stats, "hypothesis": hypothesis, "plan": plan.__dict__}, JEV_QUESTIONS) if use_ai else JevClient().judge(stats, JEV_QUESTIONS)
        result = MissionResult(mission_id, created, hypothesis, plan, stats, judge.get("scores", {}),
                               _narrative(hypothesis, plan, stats, use_ai), judge=judge.get("judge", ""),
                               planner_model=planner_model, data_sources=[plan.indicator_a, plan.indicator_b],
                               date_start=stats.get("coverage_start"), date_end=stats.get("coverage_end"), n_obs=stats.get("n_obs", 0))
        result.scores["supported_prob"] = judge.get("supported_prob")
    except Exception as exc:
        result = MissionResult(mission_id, created, hypothesis, locals().get("plan", None) or plan_mission(hypothesis)[0],
                               status="failed", error=str(exc))
    reports = ROOT / "missions" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / f"{mission_id}.md"
    json_path = reports / f"{mission_id}.json"
    result.artifacts["report_path"] = str(report_path)
    report_path.write_text(f"# {mission_id}\n\n## Hypothesis\n{hypothesis}\n\n## Plan\n```json\n{json.dumps(result.plan.__dict__, indent=2)}\n```\n\n## Statistics\n```json\n{json.dumps(result.stats, indent=2, default=str)}\n```\n\n## Scores\n```json\n{json.dumps(result.scores, indent=2)}\n```\n\n{result.narrative_md}\n", encoding="utf-8")
    payload = result.__dict__.copy()
    payload["plan"] = result.plan.__dict__
    json_path.write_text(json.dumps(payload, default=_json_default, indent=2), encoding="utf-8")
    return result
