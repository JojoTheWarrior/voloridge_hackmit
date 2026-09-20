"""Compare bulk events with public RPC receipts; retain exact numeric precision."""

import json
import pandas as pd
from access import ROOT

FILL_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"
CTF = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"


def audit_receipts():
    fills = pd.read_parquet(ROOT / "data/fills.parquet")
    bykey = {
        (str(r.transaction_hash).removeprefix("0x").lower(), int(r.log_index)): r
        for r in fills.itertuples()
    }
    rows = []
    for path in sorted((ROOT / "data/access").glob("receipt_*.body")):
        j = json.loads(path.read_bytes())
        receipt = j.get("result")
        if not isinstance(receipt, dict):
            continue
        for log in receipt["logs"]:
            topics = log["topics"]
            tx = receipt["transactionHash"]
            idx = int(log["logIndex"], 16)
            raw = log["data"].removeprefix("0x")
            words = [str(int(raw[k : k + 64], 16)) for k in range(0, len(raw), 64)]
            r = bykey.get((tx.removeprefix("0x").lower(), idx))
            match = None
            if topics[0].lower() == FILL_TOPIC and r is not None:
                expected = [
                    str(getattr(r, k))
                    for k in [
                        "maker_asset_id",
                        "taker_asset_id",
                        "maker_amount_filled",
                        "taker_amount_filled",
                        "fee",
                    ]
                ]
                match = (
                    words == expected
                    and "0x" + topics[2][-40:].lower() == r.maker
                    and "0x" + topics[3][-40:].lower() == r.taker
                )
            rows.append(
                {
                    "transaction_hash": tx,
                    "log_index": idx,
                    "contract": log["address"].lower(),
                    "topic0": topics[0].lower(),
                    "is_ctf_lifecycle_or_transfer": log["address"].lower() == CTF,
                    "is_orderfilled": topics[0].lower() == FILL_TOPIC,
                    "bulk_match": match,
                    "data_words": json.dumps(words),
                }
            )
    out = pd.DataFrame(rows)
    out.to_parquet(ROOT / "data/receipt_audit.parquet", index=False)
    summary = {
        "receipts": int(out.transaction_hash.nunique()),
        "logs": len(out),
        "ctf_logs": int(out.is_ctf_lifecycle_or_transfer.sum()),
        "orderfilled_logs": int(out.is_orderfilled.sum()),
        "bulk_exact_matches": int(out.bulk_match.fillna(False).sum()),
        "interpretation": "Exact raw-fill spot checks only; these do not establish archive completeness, lifetime wallet PnL, or forecast skill.",
    }
    (ROOT / "data/receipt_summary.json").write_text(json.dumps(summary, indent=2))
    print(summary)


if __name__ == "__main__":
    audit_receipts()
