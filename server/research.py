"""The checked-in research library, available as starting points for new missions."""
from __future__ import annotations

import json
import logging
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "research"
MAX_REFERENCE_CHARS = 100_000
log = logging.getLogger(__name__)


def list_findings(root: Path = RESEARCH_DIR) -> list[dict]:
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
            reference = json.dumps(row, ensure_ascii=False, indent=2)
            if len(reference) > MAX_REFERENCE_CHARS:
                continue
            findings.append({
                "id": f"{path.parent.name}/{index}",
                "title": row["title"].strip(),
                "summary": row.get("one_liner") if isinstance(row.get("one_liner"), str) else "",
                "source": path.parent.name,
                "verdict": row.get("verdict") if isinstance(row.get("verdict"), str) else "",
                "reference": reference,
            })
    return findings
