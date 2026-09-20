from __future__ import annotations

from collections.abc import Collection

from server.artifacts import normalise_stats

MAX_REPORT_STATS = 4
MAX_KEY_ARTIFACTS = 3
MAX_REPORT_STEPS = 8
MAX_CAVEATS = 4
MAX_NEXT_QUESTIONS = 3


def normalise_report(raw: object, known_artifact_ids: Collection[str] = ()) -> dict | None:
    """Turn Devin's snake_case `report` into the app's camelCase `Report`, minus `generatedAt`.

    Returns None until there is a headline and a summary. Over-limit lists are truncated,
    and featured artifacts the thread does not have are dropped. Never raises.
    """
    if not isinstance(raw, dict):
        return None
    headline, summary = _line(raw.get("headline")).rstrip(".").strip(), _line(raw.get("summary"))
    if not headline or not summary:
        return None
    return {
        "headline": headline,
        "summary": summary,
        "stats": normalise_stats(raw.get("stats"), MAX_REPORT_STATS),
        "keyArtifactIds": _key_artifacts(raw.get("key_artifact_ids"), known_artifact_ids),
        "steps": _steps(raw.get("steps")),
        "caveats": _lines(raw.get("caveats"), MAX_CAVEATS),
        "nextQuestions": _lines(raw.get("next_questions"), MAX_NEXT_QUESTIONS),
    }


def _key_artifacts(raw: object, known: Collection[str]) -> list[str]:
    # Filter before truncating, so an id the thread lacks does not cost a real one its place.
    ids = dict.fromkeys(artifact_id for item in _list(raw) if (artifact_id := _line(item)) in known)
    return list(ids)[:MAX_KEY_ARTIFACTS]


def _steps(raw: object) -> list[dict]:
    steps = []
    for item in _list(raw):
        if isinstance(item, dict) and (label := _line(item.get("label"))):
            steps.append({"label": label, "takeaway": _line(item.get("takeaway"))})
    return steps[:MAX_REPORT_STEPS]


def _lines(raw: object, limit: int) -> list[str]:
    return [line for item in _list(raw) if (line := _line(item))][:limit]


def _line(value: object) -> str:
    """Every report field is plain single-paragraph text, so stray line breaks are folded away."""
    return " ".join(value.split()) if isinstance(value, str) else ""


def _list(value: object) -> list:
    return value if isinstance(value, list) else []
