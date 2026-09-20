"""The checked-in research library, available as starting points for new missions."""
from __future__ import annotations

import json
import logging
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "research"
MAX_REFERENCE_CHARS = 100_000
log = logging.getLogger(__name__)


def list_findings(root: Path = RESEARCH_DIR) -> list[dict]:
    # The reviewed package supersedes older per-folder snapshots, including rows
    # whose original dictionary format could not be shown by the legacy picker.
    index = root / "library.json"
    if index.exists():
        try:
            rows = json.loads(index.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.warning("Could not read packaged research library")
            return []
        if not isinstance(rows, list):
            return []
        findings = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            if any(not isinstance(row.get(key), str) or not row[key].strip()
                   for key in ("id", "mission", "title")):
                continue
            if row["id"] in seen:
                continue
            finding = _finding(row, row["id"], row["mission"])
            if finding:
                findings.append(finding)
                seen.add(row["id"])
        return findings

    findings = []
    # Only the current top-level findings, never archived copies or user-supplied paths.
    for path in sorted(root.glob("*/findings.json")):
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.warning("Could not read research findings: %s", path.name)
            continue
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not isinstance(row.get("title"), str) or not row["title"].strip():
                continue
            finding = _finding(row, f"{path.parent.name}/{index}", path.parent.name)
            if finding:
                findings.append(finding)
    return findings


def _finding(row: dict, identity: str, source: str) -> dict | None:
    reference = json.dumps(row, ensure_ascii=False, indent=2)
    if len(reference) > MAX_REFERENCE_CHARS:
        return None
    return {
        "id": identity,
        "title": row["title"].strip(),
        "summary": row.get("one_liner") if isinstance(row.get("one_liner"), str) else "",
        "source": source,
        "verdict": row.get("verdict") if isinstance(row.get("verdict"), str) else "",
        "reference": reference,
    }
