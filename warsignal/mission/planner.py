from __future__ import annotations

import json
import re

from warsignal.ai.brain import think_json
from warsignal.ai.prompts import PLANNER_SYSTEM
from warsignal.config import CITIES, env
from warsignal.indicators import REGISTRY, catalogue_text
from .model import MissionPlan


_DOMAIN_RULES = (
    ("gdelt", ("news", "gdelt", "mention", "tone", "event"), ("gdelt.",)),
    ("finance", ("brent", "oil", "crude"), ("finance.bz=f",)),
    ("finance", ("wti",), ("finance.cl=f",)),
    ("finance", ("s&p", "sp500", "sp 500"), ("finance.^gspc",)),
    ("finance", ("vix",), ("finance.^vix",)),
    ("finance", ("gold",), ("finance.gc=f",)),
    ("finance", ("natural gas", "henry hub"), ("finance.ng=f",)),
    ("finance", ("ttf",), ("finance.ttf=f",)),
    ("weather", ("temperature", "wind", "rain", "precip"), ("weather.",)),
    ("airquality", ("pm2.5", "air quality"), ("airquality.",)),
    ("research", ("paper", "papers", "publication", "publications", "research", "openalex", "materials science"), ("research.",)),
    ("utility", ("electricity", "demand", "generation", "fuel cost", "pudl", "eia"), ("utility.",)),
)


class PlanValidationError(ValueError):
    pass


def _requested_cities(hypothesis):
    text = hypothesis.lower()
    aliases = {
        "tel aviv": "tel_aviv", "new york": "nyc_jfk", "nyc": "nyc_jfk",
        "abu dhabi": "abu_dhabi", "bandar abbas": "bandar_abbas",
        "kuwait city": "kuwait",
    }
    for alias, slug in aliases.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            text += f" {slug.replace('_', ' ')}"
    if re.search(r"\b(?:persian gulf|gulf)\b", text):
        text += " dubai doha abu dhabi kuwait bahrain bandar abbas muscat basrah"
    found = []
    for slug in CITIES:
        names = {slug.replace("_", " ")}
        if slug == "nyc_jfk":
            names.add("new york")
        if any(re.search(rf"\b{re.escape(name)}\b", text) for name in names):
            found.append(slug)
    return found


def _validate_plan(hypothesis, plan):
    if plan.indicator_a == plan.indicator_b:
        plan.mode = "single"
    if plan.mode not in {"pair", "single"}:
        raise PlanValidationError(f"invalid mission mode: {plan.mode}")
    missing = [name for name in (plan.indicator_a, plan.indicator_b) if name not in REGISTRY]
    if missing:
        raise PlanValidationError(f"invalid indicator names: {missing}")
    requested = _requested_cities(hypothesis)
    for name in (plan.indicator_a, plan.indicator_b):
        spec = REGISTRY[name]
        if (
            requested
            and spec.source in {"weather", "airquality"}
            and spec.region not in requested
        ):
            raise PlanValidationError(f"requested city {requested[0]} has no data for {spec.source}")
    return plan


def _keyword_scores(text):
    scores = {}
    aliases = {
        "iran": "irn", "israel": "isr", "tehran": "tehran", "dubai": "dubai",
        "doha": "doha", "riyadh": "riyadh", "kuwait": "kuwait",
    }
    for name, spec in REGISTRY.items():
        if spec.source == "events":
            scores[name] = 0.0
            continue
        if spec.source == "materials" or (
            spec.source == "research" and ".crossref_" not in name
        ):
            scores[name] = 0.0
            continue
        lower_name = name.lower()
        weather_terms = (
            "temperature", "wind", "rain", "precip", "pm25", "pm2.5", "no2",
            "air quality", "pollution", "dust",
        )
        if spec.source in {"weather", "airquality"} and not _requested_cities(text):
            if not any(term in text for term in weather_terms):
                scores[name] = 0.0
                continue
        score = 0.0
        for source, terms, prefixes in _DOMAIN_RULES:
            hits = sum(1 for term in terms if term in text)
            if hits and spec.source == source:
                score += 4 * hits
                if any(lower_name.startswith(prefix) for prefix in prefixes):
                    score += 3 * hits
        for alias, slug in aliases.items():
            if alias in text and (f".{slug}." in lower_name or lower_name.startswith(f"weather.{slug}.")):
                score += 5
        normalized_name = lower_name.replace("_", " ")
        for token in re.findall(r"[a-z0-9]+", text):
            if len(token) > 3 and token in normalized_name:
                score += 2
        if "return" in text or "price" in text:
            score += 2 if lower_name.endswith("log_return") else 0
        else:
            score += 2 if lower_name.endswith(("events", "temp_mean", "close")) else 0
        if lower_name.endswith(".events"):
            score += 0.25
        if "temperature" in text and lower_name.endswith("temp_mean"):
            score += 2
        if "event" in text and lower_name.endswith("events"):
            score += 2
        scores[name] = score
    return scores


def heuristic_plan(hypothesis):
    text = hypothesis.lower()
    scores = _keyword_scores(text)
    single_tone = "tone" in text and not any(
        marker in text for marker in (" vs ", " versus ", " correlate", " leads ", " related to ")
    )
    if single_tone and "gdelt.irn.tone" in REGISTRY:
        return MissionPlan(
            "gdelt.irn.tone", "gdelt.irn.tone", "level", "level", 0,
            "compare_pre_post", None, False,
            -1 if any(term in text for term in ("negative", "lower", "more negative")) else 0,
            "Single-series tone change compared across the war boundary.", "single",
        )
    ordered = sorted(scores, key=lambda name: (scores[name], name), reverse=True)
    if not ordered:
        return MissionPlan("", "")
    indicator_a = ordered[0]
    source_a = REGISTRY[indicator_a].source
    other_sources = [name for name in ordered[1:] if REGISTRY[name].source != source_a and scores[name] > 0]
    indicator_b = other_sources[0] if other_sources else (ordered[1] if len(ordered) > 1 else indicator_a)
    if "brent" in text and ("s&p" in text or "sp 500" in text):
        indicator_a, indicator_b = "finance.BZ=F.log_return", "finance.^GSPC.log_return"
    transform_a = "log_return" if "return" in text or "price" in text else "level"
    transform_b = "log_return" if "return" in text or "price" in text else "level"
    if REGISTRY[indicator_a].source in {"gdelt", "weather", "airquality", "research", "materials", "utility"}:
        transform_a = "level"
    expected = -1 if "negative" in text or "lower" in text or "decline" in text else (1 if "positive" in text or "higher" in text or "rise" in text else 0)
    return MissionPlan(indicator_a, indicator_b, transform_a, transform_b,
                       3 if "lag" in text or "lead" in text else 0,
                       "compare_pre_post" if "after" in text and ("before" in text or "changed" in text) else "full",
                       "war" if "war" in text else None, "null" in text or "control" in text, expected,
                       "Heuristic keyword overlap with source-diverse catalogue entries.")


def plan_mission(hypothesis, use_ai=True, mission_id="planning", brain_backend=None, brain_sessions=None):
    if not use_ai or brain_backend == "heuristic":
        return _validate_plan(hypothesis, _semantic_adjust(hypothesis, heuristic_plan(hypothesis))), "heuristic"
    catalogue = catalogue_text()
    if len(catalogue) > 24000:
        terms = set(re.findall(r"[a-z0-9_]+", hypothesis.lower()))
        selected = [
            line for line in catalogue.splitlines()
            if any(term in line.lower() for term in terms if len(term) > 2)
        ]
        compact = "\n".join(selected)
        catalogue = (compact + "\n" + catalogue)[:24000]
    prompt = (
        f"MISSION:\n{hypothesis}\n\n"
        "COVERAGE GUIDANCE: Prefer indicators whose coverage spans 2025-03..2026-09. "
        "ISD-only series stop in 2025-08. Event-count indicators are sparse 0/1 "
        "timeline markers for event studies, not correlation inputs.\n\n"
        f"CATALOGUE:\n{catalogue}"
    )
    last_error = None
    schema = {
        "type": "object",
        "properties": {
            "indicator_a": {"type": "string"},
            "indicator_b": {"type": "string"},
            "transform_a": {"type": "string"},
            "transform_b": {"type": "string"},
            "max_lag_days": {"type": "integer"},
            "window": {"type": "string"},
            "event_category": {"type": ["string", "null"]},
            "is_null_control": {"type": "boolean"},
            "expected_sign": {"type": "integer"},
            "rationale": {"type": "string"},
            "mode": {"type": "string"},
        },
        "required": [
            "indicator_a", "indicator_b", "transform_a", "transform_b", "max_lag_days",
            "window", "event_category", "is_null_control", "expected_sign", "rationale", "mode",
        ],
    }
    for attempt in range(2):
        try:
            result = think_json(
                PLANNER_SYSTEM,
                prompt,
                schema,
                purpose="planner",
                mission_id=mission_id,
                backend=brain_backend,
            )
            if brain_sessions is not None and result.get("_meta"):
                brain_sessions.append({
                    "purpose": "planner",
                    "backend": result["_meta"].get("backend"),
                    "session_url": result["_meta"].get("session_url"),
                })
            fields = {key: result[key] for key in MissionPlan.__dataclass_fields__ if key in result}
            plan = MissionPlan(**fields)
            plan = _validate_plan(hypothesis, _semantic_adjust(hypothesis, plan))
            meta = result.get("_meta", {})
            return plan, meta.get("model") or meta.get("backend", env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"))
        except Exception as exc:
            last_error = exc
            print(f"[planner] ai plan rejected: {exc}", flush=True)
            prompt += f"\nPlanner error: {exc}. Use exact registered indicator names."
    fallback = heuristic_plan(hypothesis)
    return _validate_plan(hypothesis, _semantic_adjust(hypothesis, fallback)), "heuristic"


def _semantic_adjust(hypothesis, plan):
    lower = hypothesis.lower()
    if "brent" in lower and "s&p" in lower:
        plan.indicator_a = "finance.BZ=F.log_return"
        plan.indicator_b = "finance.^GSPC.log_return"
        plan.transform_a = plan.transform_b = "level"
    if "after" in lower and ("before" in lower or "became" in lower or "changed" in lower):
        plan.window = "compare_pre_post"
    return plan
