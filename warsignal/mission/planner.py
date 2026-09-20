from __future__ import annotations

import json
import re

from warsignal.ai.openai_client import AIUnavailable, chat_json
from warsignal.ai.prompts import PLANNER_SYSTEM
from warsignal.config import env
from warsignal.indicators import REGISTRY, catalogue_text
from .model import MissionPlan


def heuristic_plan(hypothesis):
    text = hypothesis.lower()
    names = list(REGISTRY)
    def choose(patterns, fallback):
        for name in names:
            if any(pattern in name.lower() for pattern in patterns):
                return name
        return fallback
    a = choose(["gdelt", "weather", "research", "airquality"], names[0] if names else "")
    b = choose(["finance.bz=f.close", "finance", "weather"], names[-1] if names else "")
    if "brent" in text and ("s&p" in text or "sp 500" in text):
        return MissionPlan("finance.BZ=F.log_return", "finance.^GSPC.log_return", "level", "level", 3,
                           "compare_pre_post", None, False, -1, "Brent and S&P 500 daily return comparison.")
    if "temperature" in text or "tehran" in text:
        a = choose(["weather.tehran.temp_mean", "weather.tehran.temp"], a)
    if "brent" in text or "oil" in text:
        if "brent" in text and "s&p" not in text and "temperature" not in text and "tehran" not in text:
            a = choose(["finance.bz=f.log_return", "finance.bz=f.close"], a)
        b = choose(["finance.^gspc.log_return", "finance.^gspc.close"], b) if "s&p" in text or "sp 500" in text else choose(["finance.bz=f.log_return", "finance.bz=f.close"], b)
    transform_a = "log_return" if "return" in text or "price" in text else "level"
    transform_b = "log_return" if "return" in text or "price" in text else "level"
    expected = -1 if "negative" in text or "lower" in text or "decline" in text else (1 if "positive" in text or "higher" in text or "rise" in text else 0)
    return MissionPlan(a, b, transform_a, transform_b, 3 if "lag" in text or "lead" in text else 0,
                       "compare_pre_post" if "after" in text and ("before" in text or "changed" in text) else "full",
                       "war" if "war" in text else None, "null" in text or "control" in text, expected,
                       "Heuristic keyword match against the indicator catalogue.")


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
        plan.transform_a, plan.transform_b = "level", "level"
        plan.max_lag_days = 3
    if "after" in lower and ("before" in lower or "became" in lower or "changed" in lower):
        plan.window = "compare_pre_post"
    return plan
