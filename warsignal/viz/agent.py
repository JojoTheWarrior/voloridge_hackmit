"""AI-assisted mission visualization design with a deterministic safe fallback."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from warsignal.ai.openai_client import chat_json
from warsignal.ai.prompts import VIZ_SYSTEM
from warsignal.config import env
from warsignal.indicators import REGISTRY


def _as_dict(result):
    if isinstance(result, dict):
        return result
    data = dict(result.__dict__)
    plan = data.get("plan")
    if hasattr(plan, "__dict__"):
        data["plan"] = plan.__dict__
    return data


def default_spec(mission_result):
    result = _as_dict(mission_result)
    plan = result.get("plan") or {}
    a, b = plan.get("indicator_a"), plan.get("indicator_b")
    panels = [{"kind": "timeseries", "series": [a, b], "normalize": True, "note": "Mission indicators"}]
    if (result.get("stats", {}).get("lagged") or {}).get("best_lag", 0) != 0:
        panels.append({"kind": "lagcorr", "series": [a, b], "normalize": False, "note": "Lag correlation"})
    if plan.get("event_category"):
        panels.append({"kind": "eventstudy", "series": [a], "normalize": False, "note": "Event study"})
    return {
        "title": result.get("hypothesis", "WarSignal mission"),
        "panels": panels[:3],
        "events": [plan["event_category"]] if plan.get("event_category") else [],
        "highlight_dates": [date for date in (
            result.get("stats", {}).get("coverage_start"),
            result.get("stats", {}).get("coverage_end"),
        ) if date],
        "color_theme": "dark",
    }


def _compact(result):
    data = _as_dict(result)
    stats = dict(data.get("stats") or {})
    event = stats.get("event_study")
    if isinstance(event, dict):
        stats["event_study"] = {key: value for key, value in event.items() if key != "per_event"}
    return {"hypothesis": data.get("hypothesis"), "plan": data.get("plan"), "stats": stats}


def _valid(spec, result):
    fallback = default_spec(result)
    if not isinstance(spec, dict):
        return fallback
    allowed = {"timeseries", "scatter", "lagcorr", "eventstudy"}
    panels = []
    for panel in spec.get("panels", []):
        if not isinstance(panel, dict) or panel.get("kind") not in allowed:
            continue
        names = [name for name in panel.get("series", []) if name in REGISTRY]
        if panel["kind"] == "timeseries":
            plan = (_as_dict(result).get("plan") or {})
            required = [plan.get("indicator_a"), plan.get("indicator_b")]
            names = [name for name in required if name in REGISTRY] or names
        if names:
            panel = dict(panel)
            panel["series"] = names
            panel["normalize"] = bool(panel.get("normalize", False))
            panel["note"] = str(panel.get("note", ""))
            panels.append(panel)
    plan = _as_dict(result).get("plan") or {}
    a, b = plan.get("indicator_a"), plan.get("indicator_b")
    if not any(panel["kind"] == "timeseries" for panel in panels):
        panels.insert(0, {"kind": "timeseries", "series": [a, b], "normalize": True, "note": "Mission indicators"})
    spec = {
        "title": str(spec.get("title") or fallback["title"]),
        "panels": panels[:3],
        "events": [event for event in spec.get("events", []) if isinstance(event, str)],
        "highlight_dates": [date for date in spec.get("highlight_dates", []) if isinstance(date, str)][:6],
        "color_theme": spec.get("color_theme") if spec.get("color_theme") in {"dark", "light"} else "dark",
    }
    return spec


def _codegen(result, spec, allow_exec):
    mission_id = _as_dict(result).get("mission_id", "mission")
    target = Path("missions/viz_generated") / f"{mission_id}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    prompt = (
        "Write only Python source defining draw(surface, ctx). ctx has series, dates, stats, fonts, palette. "
        "Use pygame drawing only; do not import subprocess, os, pathlib, or read files. "
        f"Mission visualization spec: {json.dumps(spec, default=str)}"
    )
    try:
        generated = chat_json(VIZ_SYSTEM, prompt, model=env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"))
        source = generated.get("code", "")
        if not isinstance(source, str) or "def draw(" not in source:
            return None
        target.write_text(source, encoding="utf-8")
        if allow_exec:
            subprocess.run(
                [sys.executable, "-c", f"import importlib.util; s=importlib.util.spec_from_file_location('generated', {str(target)!r}); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert callable(m.draw)"],
                check=True,
                timeout=60,
            )
        return str(target)
    except Exception:
        return None


def design_viz(mission_result, codegen=False, allow_exec=False):
    """Return a validated VizSpec; generated code is never executed without both flags."""
    fallback = default_spec(mission_result)
    if not env("OPENAI_API_KEY"):
        if codegen:
            _codegen(mission_result, fallback, allow_exec and codegen)
        return fallback
    try:
        response = chat_json(
            VIZ_SYSTEM,
            json.dumps(_compact(mission_result), default=str),
            model=env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"),
        )
        spec = _valid(response, mission_result)
    except Exception:
        spec = fallback
    if codegen:
        _codegen(mission_result, spec, allow_exec and codegen)
    return spec
