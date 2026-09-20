"""AI-assisted mission visualization design with a deterministic safe fallback."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from warsignal.ai.brain import think_json
from warsignal.ai.prompts import VIZ_SYSTEM
from warsignal.indicators import REGISTRY


def _as_dict(result):
    if isinstance(result, dict):
        return result
    data = dict(result.__dict__)
    plan = data.get("plan")
    if hasattr(plan, "__dict__"):
        data["plan"] = plan.__dict__
    return data


def _coverage_note(result):
    stats = result.get("stats") or {}
    n = stats.get("n_obs") or result.get("n_obs")
    window = (result.get("plan") or {}).get("window") or "full"
    return f"{n} aligned days · {window} window" if n else f"{window} window"


def _lag_note(result):
    lagged = (result.get("stats") or {}).get("lagged") or {}
    best, r = lagged.get("best_lag"), lagged.get("best_r")
    if r is None and best is not None and lagged.get("lags") and best in lagged["lags"]:
        r = lagged["r"][lagged["lags"].index(best)]
    if best is None or r is None:
        return "cross-correlation by lag"
    perm = (result.get("stats") or {}).get("perm_p")
    tail = f"; perm p={float(perm):.2f}" if isinstance(perm, (int, float)) else ""
    return f"peak r={float(r):+.2f} at {int(best):+d}d{tail}"


def default_spec(mission_result):
    result = _as_dict(mission_result)
    plan = result.get("plan") or {}
    a, b = plan.get("indicator_a"), plan.get("indicator_b")
    names = [a] if plan.get("mode") == "single" else [a, b]
    pair = plan.get("mode") != "single"
    panels = [{"kind": "timeseries", "series": names, "normalize": pair, "note": _coverage_note(result)}]
    lagged = result.get("stats", {}).get("lagged") or {}
    if pair and lagged.get("lags"):
        panels.append({"kind": "lagcorr", "series": [a, b], "normalize": False, "note": _lag_note(result)})
    if plan.get("event_category"):
        panels.append({"kind": "eventstudy", "series": [a], "normalize": False,
                       "note": f"pre vs post {plan['event_category']} events"})
    elif pair and len(panels) < 3:
        panels.append({"kind": "scatter", "series": [a, b], "normalize": False, "note": "aligned daily pairs"})
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
        if (_as_dict(result).get("plan") or {}).get("mode") == "single" and panel.get("kind") == "scatter":
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


def _codegen(result, spec, allow_exec, brain_backend=None, brain_sessions=None):
    mission_id = _as_dict(result).get("mission_id", "mission")
    target = Path("missions/viz_generated") / f"{mission_id}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    prompt = (
        "Write only Python source defining draw(surface, ctx). ctx has series, dates, stats, fonts, palette. "
        "Use pygame drawing only; do not import subprocess, os, pathlib, or read files. "
        f"Mission visualization spec: {json.dumps(spec, default=str)}"
    )
    try:
        generated = think_json(
            VIZ_SYSTEM,
            prompt,
            {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
            purpose="viz_codegen",
            mission_id=mission_id,
            backend=brain_backend,
        )
        if brain_sessions is not None and generated.get("_meta"):
            brain_sessions.append({
                "purpose": "viz_codegen",
                "backend": generated["_meta"].get("backend"),
                "session_url": generated["_meta"].get("session_url"),
            })
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


def design_viz(mission_result, codegen=False, allow_exec=False, brain_backend=None, brain_sessions=None):
    """Return a validated VizSpec; generated code is never executed without both flags."""
    fallback = default_spec(mission_result)
    try:
        response = think_json(
            VIZ_SYSTEM,
            json.dumps(_compact(mission_result), default=str),
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "panels": {"type": "array"},
                    "events": {"type": "array"},
                    "highlight_dates": {"type": "array"},
                    "color_theme": {"type": "string"},
                },
            },
            purpose="viz_design",
            mission_id=_as_dict(mission_result).get("mission_id", "mission"),
            backend=brain_backend,
        )
        if brain_sessions is not None and response.get("_meta"):
            brain_sessions.append({
                "purpose": "viz_design",
                "backend": response["_meta"].get("backend"),
                "session_url": response["_meta"].get("session_url"),
            })
        spec = _valid(response, mission_result)
    except Exception:
        spec = fallback
    if codegen:
        _codegen(mission_result, spec, allow_exec and codegen, brain_backend, brain_sessions)
    return spec
