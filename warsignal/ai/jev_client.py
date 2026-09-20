from __future__ import annotations

import argparse
import json
import math
import time

import requests

from warsignal.ai.openai_client import AIUnavailable, chat_json
from warsignal.ai.prompts import FALLBACK_JUDGE_SYSTEM
from warsignal.config import env


class JevClient:
    def judge(self, state: dict, questions: dict) -> dict:
        fallback = _fallback(state, questions)
        key = env("TYPESAFE_API_KEY")
        if not key:
            return fallback
        body = {"model": "jev-latest", "state": json.dumps(state), "questions": [
            {"id": key_, **value} for key_, value in questions.items()
        ]}
        try:
            response = requests.post("https://api.typesafe.ai/v1/systemone", json=body,
                                     headers={"Authorization": f"Bearer {key}"}, timeout=60)
            response.raise_for_status()
            parsed = response.json()
            return _normalise(parsed, "jev", "jev-latest")
        except Exception:
            return fallback


def _fallback(state, questions):
    try:
        return _openai_fallback(state)
    except Exception:
        time.sleep(1)
        try:
            return _openai_fallback(state)
        except Exception:
            corr = abs(float((state.get("correlation") or {}).get("pearson_r") or 0))
            n = float(state.get("n_obs") or 0)
            perm = float(state.get("perm_p") or 1)
            validity = max(0, min(10, 3 * corr + min(3, math.log10(max(n, 1))) + (3 if perm < .05 else 0)))
            plan = state.get("plan") or {}
            indicator_a = plan.get("indicator_a", state.get("indicator_a", ""))
            indicator_b = plan.get("indicator_b", state.get("indicator_b", ""))
            source_a, source_b = indicator_a.split(".", 1)[0], indicator_b.split(".", 1)[0]
            cross_domain = source_a != source_b
            interesting = max(0, min(10, 4 * corr + (2 if state.get("pre_post") else 0) + (2 if cross_domain else 0)))
            unexpected = max(0, min(10, 5 * corr + (2 if cross_domain else 0)))
            return {"scores": {"validity": validity, "interestingness": interesting, "unexpectedness": unexpected},
                    "supported_prob": float(1 if perm < .05 else 0), "judge": "heuristic", "model": "heuristic", "raw": {}}


def _openai_fallback(state):
    result = chat_json(FALLBACK_JUDGE_SYSTEM, json.dumps(state, default=str),
                       model=env("WARSIGNAL_CHEAP_MODEL", "gpt-5-mini"))
    scores = {key: float((result.get(key) or {}).get("score", 0)) for key in ("validity", "interestingness", "unexpectedness")}
    supported = result.get("supported") or {}
    return {"scores": scores, "supported_prob": float(supported.get("probability", 0.0)),
            "judge": "openai-fallback", "model": env("WARSIGNAL_CHEAP_MODEL", "gpt-5-mini"), "raw": result}


def _normalise(data, judge, model):
    scores = {}
    for key in ("validity", "interestingness", "unexpectedness"):
        item = data.get(key, {}) if isinstance(data, dict) else {}
        if isinstance(item, dict):
            scores[key] = float(item.get("score", item.get("probability", 0)))
        else:
            scores[key] = float(item)
    supported = data.get("supported", {}) if isinstance(data, dict) else {}
    if isinstance(supported, dict):
        probability = supported.get("probability", supported.get("probabilities", 0))
    else:
        probability = supported
    return {"scores": scores, "supported_prob": float(probability or 0), "judge": judge, "model": model, "raw": data}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        print("jev" if env("TYPESAFE_API_KEY") else ("openai-fallback" if env("OPENAI_API_KEY") else "heuristic"))
