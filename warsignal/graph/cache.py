from __future__ import annotations

import difflib
import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

STOPWORDS = {"the", "of", "a", "an", "me", "show", "plot", "graph", "please", "chart", "draw"}


def normalise(text: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", str(text).lower()).split()
    return " ".join(token for token in tokens if token not in STOPWORDS)


def load_records(graphs_dir: Path) -> list[dict]:
    records = []
    if not Path(graphs_dir).exists():
        return records
    for folder in sorted(Path(graphs_dir).iterdir()):
        prompt_file, plan_file = folder / "prompt.txt", folder / "plan.json"
        if not prompt_file.exists() or not plan_file.exists():
            continue
        try:
            records.append({
                "folder": folder.name,
                "prompt": prompt_file.read_text(encoding="utf-8").strip(),
                "plan": json.loads(plan_file.read_text(encoding="utf-8")),
            })
        except Exception:
            continue
    return records


def similarity(a: str, b: str) -> float:
    na, nb = normalise(a), normalise(b)
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return max(ratio, jaccard)


def find_match(prompt: str, graphs_dir: Path, confirm=None) -> dict | None:
    candidates = []
    for record in load_records(graphs_dir):
        score = similarity(prompt, record["prompt"])
        if score >= 0.92:
            return record
        if score >= 0.55:
            candidates.append((score, record))
    candidates.sort(key=lambda item: item[0], reverse=True)
    top = [record for _, record in candidates[:5]]
    if top and callable(confirm):
        try:
            folder = confirm(prompt, top)
        except Exception as exc:
            log.warning("cache confirm failed: %s", exc)
            return None
        if folder:
            return next((record for record in top if record["folder"] == folder), None)
    return None


def llm_confirm(prompt: str, candidates: list[dict]) -> str | None:
    from warsignal.ai.openai_client import AIUnavailable, chat_json
    try:
        options = [{"folder": c["folder"], "prompt": c["prompt"]} for c in candidates]
        result = chat_json(
            "You decide whether a new chart request is the same chart as an existing one. "
            "Return {\"match\": <folder or null>}.",
            f"new prompt: {prompt}\nexisting: {json.dumps(options)}",
            model="gpt-5-mini",
        )
        match = result.get("match")
        return str(match) if match else None
    except AIUnavailable:
        return None
