from __future__ import annotations

import json
import math
import shutil
import secrets
from datetime import datetime, timezone
from pathlib import Path

from warsignal.ai.jev_client import JevClient
from warsignal.ai.prompts import JEV_QUESTIONS, NARRATIVE_SYSTEM
from warsignal.ai.openai_client import chat_text
from warsignal.analysis.stats import align, apply_window, run_all, run_single, transform
from warsignal.config import START, END
from warsignal.indicators import get_series
from warsignal.util import to_jsonable
from .model import MissionResult
from .planner import heuristic_plan, plan_mission
from .publish import publish_run, write_run_folder

ROOT = Path(__file__).resolve().parents[2]


def _json_default(value):
    return to_jsonable(value)


def _narrative(hypothesis, plan, stats, use_ai):
    if use_ai:
        try:
            return chat_text(NARRATIVE_SYSTEM, json.dumps({"hypothesis": hypothesis, "plan": plan.__dict__, "stats": stats}),
                             model=__import__("warsignal.config", fromlist=["env"]).env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"))[0]
        except Exception:
            pass
    corr = (stats.get("correlation") or {}).get("pearson_r")
    lag_unit = stats.get("lag_unit", "days")
    if plan.mode == "single":
        change = (stats.get("pre_post") or {}).get("mean_diff")
        welch_p = (stats.get("pre_post") or {}).get("welch_p")
        return (
            f"**Verdict:** {'supported' if stats.get('sign_matches_expectation') else 'not supported'} "
            f"(mean change={change!s}, n={stats.get('n_obs', 0)}).\n\n"
            f"The post-boundary mean changed by {change!s}; Welch p={welch_p!s}.\n\n"
            "This difference is descriptive, not causal; seasonality, common shocks, and boundary selection "
            "remain possible confounders."
        )
    return (f"**Verdict:** {'supported' if stats.get('sign_matches_expectation') else 'not supported'} "
            f"(Pearson r={corr!s}, n={stats.get('n_obs', 0)}).\n\n"
            f"The best tested lag was {(stats.get('lagged') or {}).get('best_lag')} {lag_unit} with "
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


def _heuristic_judge(plan, stats):
    corr = abs(float((stats.get("correlation") or {}).get("pearson_r") or 0))
    n_obs = float(stats.get("n_obs") or 0)
    perm = float(stats.get("perm_p") or 1)
    cross_domain = plan.indicator_a.split(".", 1)[0] != plan.indicator_b.split(".", 1)[0]
    validity = max(0, min(10, 3 * corr + min(3, math.log10(max(n_obs, 1))) + (3 if perm < .05 else 0)))
    interesting = max(0, min(10, 4 * corr + (2 if stats.get("pre_post") else 0) + (2 if cross_domain else 0)))
    unexpected = max(0, min(10, 5 * corr + (2 if cross_domain else 0)))
    return {
        "scores": {"validity": validity, "interestingness": interesting, "unexpectedness": unexpected},
        "supported_prob": float(1 if perm < .05 else 0),
        "judge": "heuristic",
        "model": "heuristic",
        "confidence": {},
        "raw": {},
    }


def run_mission(hypothesis, mission_id=None, use_ai=True, viz=False, show=False, publish=False):
    mission_id = mission_id or f"M{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3)}"
    created = datetime.now(timezone.utc).isoformat()
    raw_a = raw_b = transformed_a = transformed_b = None
    judge = {}
    try:
        plan, planner_model = plan_mission(hypothesis, use_ai=use_ai)
        a = raw_a = get_series(plan.indicator_a, START, END)
        if plan.mode == "single":
            b = None
        else:
            b = raw_b = get_series(plan.indicator_b, START, END)
        overlap = a.dropna() if plan.mode == "single" else align(a, b)
        monthly = len(overlap) > 1 and overlap.index.to_series().diff().median() > __import__("pandas").Timedelta(days=20)
        if len(overlap) < (12 if monthly else 20):
            def coverage(series):
                valid = series.dropna()
                if valid.empty:
                    return "no dates (n=0)"
                return f"{valid.index.min().date()}..{valid.index.max().date()} (n={len(valid)})"
            detail = f"{plan.indicator_a} covers {coverage(a)}"
            if b is not None:
                detail += f", {plan.indicator_b} covers {coverage(b)}"
            raise ValueError(f"insufficient overlap: {detail}")
        from warsignal.indicators.events import load_timeline
        stats = run_single(plan, a, load_timeline()) if plan.mode == "single" else run_all(plan, a, b, load_timeline())
        judge = (
            JevClient().judge(_judge_state(hypothesis, plan, stats), JEV_QUESTIONS)
            if use_ai else _heuristic_judge(plan, stats)
        )
        result = MissionResult(mission_id, created, hypothesis, plan, stats, judge.get("scores", {}),
                               _narrative(hypothesis, plan, stats, use_ai), judge=judge.get("judge", ""),
                               planner_model=planner_model, data_sources=[plan.indicator_a] if plan.mode == "single" else [plan.indicator_a, plan.indicator_b],
                               date_start=stats.get("coverage_start"), date_end=stats.get("coverage_end"), n_obs=stats.get("n_obs", 0))
        result.scores["supported_prob"] = judge.get("supported_prob")
        result.scores["judge_model"] = judge.get("model", "")
        transformed_a = apply_window(transform(a, plan.transform_a), plan.window)
        transformed_b = None if plan.mode == "single" else apply_window(transform(b, plan.transform_b), plan.window)
    except Exception as exc:
        failed_plan = locals().get("plan", None)
        if failed_plan is None:
            try:
                failed_plan, failed_model = plan_mission(hypothesis, use_ai=use_ai)
            except Exception:
                failed_plan, failed_model = heuristic_plan(hypothesis), "heuristic"
        else:
            failed_model = locals().get("planner_model", "")
        result = MissionResult(
            mission_id, created, hypothesis, failed_plan, status="failed", error=str(exc),
            planner_model=failed_model,
            data_sources=[failed_plan.indicator_a] if failed_plan.mode == "single" else [failed_plan.indicator_a, failed_plan.indicator_b],
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
    folder = write_run_folder(
        result,
        raw_a=raw_a,
        raw_b=raw_b,
        transformed_a=transformed_a,
        transformed_b=transformed_b,
        judge=judge,
    )
    if viz_path := result.artifacts.get("viz_path"):
        folder_viz = folder / "viz.png"
        shutil.copyfile(viz_path, folder_viz)
        result.artifacts["viz_path"] = str(folder_viz)
    result.artifacts["run_folder"] = str(folder)
    result.artifacts["report_path"] = str(folder / "note.md")
    payload = result.__dict__.copy()
    payload["plan"] = result.plan.__dict__
    json_path.write_text(json.dumps(payload, default=_json_default, indent=2), encoding="utf-8")
    if publish:
        publish_run(folder)
    return result
