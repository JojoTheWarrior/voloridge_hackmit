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
from .planner import heuristic_plan, plan_mission

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


def _judge_state(hypothesis, plan, stats):
    compact_stats = dict(stats)
    event_study = compact_stats.get("event_study")
    if isinstance(event_study, dict):
        compact_stats["event_study"] = {
            key: value for key, value in event_study.items() if key != "per_event"
        }
    state = {"hypothesis": hypothesis, "plan": plan.__dict__, "stats": compact_stats}
    encoded = json.dumps(state, default=_json_default)
    if len(encoded) > 6000:
        state["stats"].pop("event_study", None)
    return state


def run_mission(hypothesis, mission_id=None, use_ai=True, viz=False, show=False):
    mission_id = mission_id or f"M{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3)}"
    created = datetime.now(timezone.utc).isoformat()
    try:
        plan, planner_model = plan_mission(hypothesis, use_ai=use_ai)
        a = get_series(plan.indicator_a, START, END)
        b = get_series(plan.indicator_b, START, END)
        overlap = __import__("pandas").concat([a.rename("a"), b.rename("b")], axis=1).dropna()
        if len(overlap) < 20:
            def coverage(series):
                valid = series.dropna()
                if valid.empty:
                    return "no dates (n=0)"
                return f"{valid.index.min().date()}..{valid.index.max().date()} (n={len(valid)})"
            raise ValueError(
                f"insufficient overlap: {plan.indicator_a} covers {coverage(a)}, "
                f"{plan.indicator_b} covers {coverage(b)}"
            )
        from warsignal.indicators.events import load_timeline
        stats = run_all(plan, a, b, load_timeline())
        judge = JevClient().judge(_judge_state(hypothesis, plan, stats), JEV_QUESTIONS) if use_ai else JevClient().judge(stats, JEV_QUESTIONS)
        result = MissionResult(mission_id, created, hypothesis, plan, stats, judge.get("scores", {}),
                               _narrative(hypothesis, plan, stats, use_ai), judge=judge.get("judge", ""),
                               planner_model=planner_model, data_sources=[plan.indicator_a, plan.indicator_b],
                               date_start=stats.get("coverage_start"), date_end=stats.get("coverage_end"), n_obs=stats.get("n_obs", 0))
        result.scores["supported_prob"] = judge.get("supported_prob")
        result.scores["judge_model"] = judge.get("model", "")
    except Exception as exc:
        failed_plan = locals().get("plan", None)
        if failed_plan is None:
            try:
                failed_plan, failed_model = plan_mission(hypothesis)
            except Exception:
                failed_plan, failed_model = heuristic_plan(hypothesis), "heuristic"
        else:
            failed_model = locals().get("planner_model", "")
        result = MissionResult(
            mission_id, created, hypothesis, failed_plan, status="failed", error=str(exc),
            planner_model=failed_model, data_sources=[failed_plan.indicator_a, failed_plan.indicator_b],
        )
    reports = ROOT / "missions" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / f"{mission_id}.md"
    json_path = reports / f"{mission_id}.json"
    result.artifacts["report_path"] = str(report_path)
    report_path.write_text(
        f"# {mission_id}\n\n## Hypothesis\n{hypothesis}\n\n## Plan\n```json\n{json.dumps(result.plan.__dict__, indent=2)}\n```\n\n"
        f"Planner model: `{result.planner_model}`\n\nJudge: `{result.judge}`\n"
        f"Judge model: `{result.scores.get('judge_model', '')}`\n\n## Statistics\n```json\n"
        f"{json.dumps(result.stats, indent=2, default=str)}\n```\n\n## Scores\n```json"
        f"\n{json.dumps(result.scores, indent=2)}\n```\n\n{result.narrative_md}\n",
        encoding="utf-8",
    )
    payload = result.__dict__.copy()
    payload["plan"] = result.plan.__dict__
    json_path.write_text(json.dumps(payload, default=_json_default, indent=2), encoding="utf-8")
    if viz or show:
        from warsignal.viz.agent import design_viz
        from warsignal.viz.pygame_viz import render

        spec = design_viz(result)
        viz_path = reports / f"{mission_id}.png"
        render(spec, json_path, viz_path, interactive=False)
        result.artifacts["viz_path"] = str(viz_path)
        payload["artifacts"] = result.artifacts
        json_path.write_text(json.dumps(payload, default=_json_default, indent=2), encoding="utf-8")
        if show:
            render(spec, json_path, viz_path, interactive=True)
    return result
