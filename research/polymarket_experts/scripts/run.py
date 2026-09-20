"""Offline reproducible data audit and explicitly blocked research outputs."""

import json
import hashlib
import importlib.metadata
from datetime import datetime, timezone
from access import ROOT
from ingest import main as ingest
from receipt_audit import audit_receipts
from publish import main as publish


def main():
    expected = (ROOT / "prereg.sha256").read_text().split()[0]
    assert hashlib.sha256((ROOT / "prereg.json").read_bytes()).hexdigest() == expected
    ingest()
    audit_receipts()
    publish()
    sources = []
    for p in sorted((ROOT / "data").rglob("*")):
        if p.is_file() and ("access" in p.parts or "raw" in p.parts):
            sources.append(
                {
                    "path": str(p.relative_to(ROOT)),
                    "bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
            )
    (ROOT / "data/source_manifest.json").write_text(json.dumps(sources, indent=2))
    env = {
        "at": datetime.now(timezone.utc).isoformat(),
        "packages": {
            p: importlib.metadata.version(p)
            for p in [
                "numpy",
                "pandas",
                "pyarrow",
                "scipy",
                "matplotlib",
                "requests",
                "pytest",
                "ruff",
                "pycryptodome",
            ]
        },
    }
    (ROOT / "data/environment.json").write_text(json.dumps(env, indent=2))


if __name__ == "__main__":
    main()
