from __future__ import annotations

import json
import re

from warsignal.ai.openai_client import AIUnavailable, chat_json
from warsignal.ai.prompts import PLANNER_SYSTEM
from warsignal.config import env
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
    ("research", ("publication", "publications", "research", "openalex"), ("research.",)),
    ("materials", ("materials project",), ("materials.",)),
    ("utility", ("electricity", "demand", "generation", "fuel cost", "pudl", "eia"), ("utility.",)),
)


def _keyword_scores(text):
    scores = {}
    aliases = {
        "iran": "irn", "israel": "isr", "tehran": "tehran", "dubai": "dubai",
        "doha": "doha", "riyadh": "riyadh", "kuwait": "kuwait",
    }
    for name, spec in REGISTRY.items():
        lower_name = name.lower()
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


def plan_mission(hypothesis):
    if not env("OPENAI_API_KEY"):
        return _semantic_adjust(hypothesis, heuristic_plan(hypothesis)), "heuristic"
    prompt = f"MISSION:\n{hypothesis}\n\nCATALOGUE:\n{catalogue_text()}"
    for attempt in range(2):
        try:
            result = chat_json(PLANNER_SYSTEM, prompt, model=env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"))
            fields = {key: result[key] for key in MissionPlan.__dataclass_fields__ if key in result}
            plan = MissionPlan(**fields)
            missing = [x for x in (plan.indicator_a, plan.indicator_b) if x not in REGISTRY]
            if missing:
                prompt += f"\nInvalid indicator names: {missing}. Choose exact names from catalogue."
                continue
            return _semantic_adjust(hypothesis, plan), result.get("_meta", {}).get("model", env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"))
        except Exception as exc:
            prompt += f"\nPlanner error: {exc}. Use exact registered indicator names."
    return _semantic_adjust(hypothesis, heuristic_plan(hypothesis)), "heuristic"


def _semantic_adjust(hypothesis, plan):
    lower = hypothesis.lower()
    if "brent" in lower and "s&p" in lower:
        plan.indicator_a = "finance.BZ=F.log_return"
        plan.indicator_b = "finance.^GSPC.log_return"
        plan.transform_a = plan.transform_b = "level"
    if "gdelt" in lower and "brent" in lower:
        plan.indicator_a = "gdelt.irn.events" if "gdelt.irn.events" in REGISTRY else plan.indicator_a
        plan.indicator_b = "finance.BZ=F.log_return"
        plan.transform_a = "level"
        plan.transform_b = "log_return" if "return" in lower else "level"
        plan.max_lag_days = 3
    if "after" in lower and ("before" in lower or "became" in lower or "changed" in lower):
        plan.window = "compare_pre_post"
    return plan
