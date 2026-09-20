from __future__ import annotations

import os
import time

from warsignal.config import env


class AIUnavailable(RuntimeError):
    pass


def _client():
    key = env("OPENAI_API_KEY")
    if not key:
        raise AIUnavailable("OPENAI_API_KEY is not set")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIUnavailable("openai package is not installed") from exc
    return OpenAI(api_key=key)


def _call(system, user, model, max_tokens, json_mode=False):
    client = _client()
    kwargs = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
             "max_tokens": max_tokens}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    last = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            return content, {"model": model, "usage": usage.model_dump() if usage and hasattr(usage, "model_dump") else str(usage)}
        except Exception as exc:
            last = exc
            if attempt == 0:
                time.sleep(1)
    raise AIUnavailable(str(last))


def chat_json(system, user, model="gpt-5.1", max_tokens=2000):
    import json
    content, meta = _call(system, user, model, max_tokens, True)
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIUnavailable(f"invalid JSON response: {exc}") from exc
    result["_meta"] = meta
    return result


def chat_text(system, user, model="gpt-5.1", max_tokens=2000):
    return _call(system, user, model, max_tokens, False)
