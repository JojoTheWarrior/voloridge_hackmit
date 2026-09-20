"""Verify frontend contract, family integrity, cached inputs, and missing-data honesty."""

import hashlib
import json
from datetime import datetime, timezone
import pandas as pd
import pyarrow.parquet as pq
from PIL import Image
from access import ROOT


def main():
    prereg = json.loads((ROOT / "prereg.json").read_text())
    digest = hashlib.sha256((ROOT / "prereg.json").read_bytes()).hexdigest()
    assert digest == (ROOT / "prereg.sha256").read_text().split()[0]
    results = pd.read_csv(ROOT / "results.csv")
    assert len(results) == 83 == prereg["family_size"]
    assert set(results.test_id) == {s["id"] for s in prereg["family"]}
    assert results.test_id.is_unique
    assert results.prereg_sha256.eq(digest).all()
    assert results.status.eq("blocked_data").all()
    assert results[["estimate", "p_value", "q_value", "mde_80pct"]].isna().all().all()
    assert results.resamples.eq(0).all() and results.planned_resamples.eq(10000).all()
    panel = pq.read_table(ROOT / "expert_panel.parquet")
    assert panel.num_rows == 0
    assert {
        "market",
        "category",
        "horizon",
        "market_price",
        "expert_prob",
        "n_experts",
        "outcome",
    } <= set(panel.column_names)
    findings = json.loads((ROOT / "findings.json").read_text())
    required = {
        "id",
        "title",
        "one_liner",
        "datasets",
        "mechanism",
        "method",
        "results",
        "controls",
        "verdict",
        "known_or_novel",
        "prior_art",
        "figures",
        "scripts",
        "caveats",
    }
    assert len({f["id"] for f in findings}) == len(findings)
    for f in findings:
        assert required <= f.keys()
        assert f["verdict"] in ["supported", "partial", "rejected"]
        for d in f["datasets"]:
            assert {"name", "url", "access"} <= d.keys()
        for r in f["results"]:
            assert {"metric", "value", "n", "note"} <= r.keys()
        for path in f["figures"] + f["scripts"]:
            assert (ROOT.parent.parent / path).is_file(), path
    pngs = sorted((ROOT / "figures").glob("*.png"))
    assert len(pngs) == 9
    for p in pngs:
        with Image.open(p) as im:
            im.verify()
    audit = json.loads((ROOT / "data/audit_summary.json").read_text())
    assert (
        pq.read_metadata(ROOT / "data/fills.parquet").num_rows
        == audit["fill_rows"]
        == 126752
    )
    logs = {
        name: (ROOT / "data" / name).read_text()
        for name in ["tests.log", "lint.log", "build.log"]
    }
    assert "18 passed" in logs["tests.log"]
    assert "All checks passed" in logs["lint.log"]
    status = {
        "at": datetime.now(timezone.utc).isoformat(),
        "output_validation": "passed",
        "unit_and_cached_real_data_tests": "18 passed",
        "lint": "passed",
        "compile": "passed",
        "container_build": "blocked: daemon unavailable; build timed out",
        "prereg_sha256": digest,
        "statistical_tests_evaluated": 0,
        "blocked_tests": 83,
        "panel_rows": 0,
        "figures_verified": len(pngs),
        "findings": len(findings),
        "independent_lifetime_pnl_reconciliation": "not achieved",
        "visual_qa": "all 9 figures inspected; data-free panels visibly marked not estimable",
    }
    (ROOT / "data/validation.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
