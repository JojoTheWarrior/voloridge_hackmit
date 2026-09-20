from __future__ import annotations

from warsignal.ai.devin_client import BrainUnavailable, DevinBrain
from warsignal.ai.openai_client import chat_json, chat_text
from warsignal.config import env


def _identity(purpose, mission_id):
    return (
        f"WarSignal {purpose} · {mission_id}",
        ["warsignal", f"purpose:{purpose}", f"mission:{mission_id}"],
    )


def _backend(override):
    return (override or env("WARSIGNAL_BRAIN", "devin")).lower()


def _openai_json(system, user, schema):
    result = chat_json(system, user, model=env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"))
    result.setdefault("_meta", {})
    result["_meta"].update({"backend": "openai", "session_url": None})
    return result


def think_json(system, user, schema, *, purpose, mission_id, backend=None):
    selected = _backend(backend)
    title, tags = _identity(purpose, mission_id)
    if selected == "heuristic":
        raise BrainUnavailable("heuristic brain selected")
    if selected == "devin":
        try:
            if env("DEVIN_API_KEY"):
                return DevinBrain().ask_json(
                    system,
                    user,
                    schema,
                    title=title,
                    tags=tags,
                )
            raise BrainUnavailable("DEVIN_API_KEY is not set")
        except BrainUnavailable as exc:
            print(f"[brain] devin unavailable ({exc}); falling back to openai", flush=True)
            selected = "openai"
    if selected == "openai":
        return _openai_json(system, user, schema)
    raise BrainUnavailable(f"unknown brain backend: {selected}")


def think_text(system, user, *, purpose, mission_id, backend=None):
    selected = _backend(backend)
    title, tags = _identity(purpose, mission_id)
    if selected == "heuristic":
        raise BrainUnavailable("heuristic brain selected")
    if selected == "devin":
        try:
            if env("DEVIN_API_KEY"):
                text, meta = DevinBrain().ask_text(
                    system,
                    user,
                    title=title,
                    tags=tags,
                )
                return text, meta
            raise BrainUnavailable("DEVIN_API_KEY is not set")
        except BrainUnavailable as exc:
            print(f"[brain] devin unavailable ({exc}); falling back to openai", flush=True)
            selected = "openai"
    if selected == "openai":
        text, meta = chat_text(
            system,
            user,
            model=env("WARSIGNAL_PLANNER_MODEL", "gpt-5.1"),
        )
        meta = dict(meta or {})
        meta.update({"backend": "openai", "session_url": None})
        return text, meta
    raise BrainUnavailable(f"unknown brain backend: {selected}")
