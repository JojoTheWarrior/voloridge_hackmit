"""Freeze sibling metadata read-only, ingest all cached bulk rows, audit coverage."""

import gzip
import hashlib
import json
import shutil
import pandas as pd
from ledger import decode_v1_maker
from access import ROOT

EXCHANGE = {
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e",
    "0xc5d563a36ae78145c45a50134d48a1215220f80a",
}


def category(question, tags):
    s = (question + " " + " ".join(tags)).lower()
    for cat, words in [
        ("NBA", ["nba"]),
        ("NFL", ["nfl", "super bowl"]),
        ("soccer", ["soccer", "premier league", "champions league", "fifa"]),
        ("weather", ["temperature", "weather", "hottest", "rainfall"]),
        ("crypto_price", ["bitcoin", "ethereum", "btc", "eth price", "solana"]),
        ("politics", ["election", "president", "senate", "trump", "biden"]),
        ("other_sports", ["sports", "mlb", "nhl", "tennis", "cricket"]),
        ("culture", ["oscars", "grammy", "box office", "culture"]),
    ]:
        if any(w in s for w in words):
            return cat
    return "unclassified"


def main():
    parts = sorted((ROOT / "data/raw").glob("v1_*.parquet"))
    x = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    for c in ["maker", "taker", "transaction_hash"]:
        x[c] = x[c].str.lower()
    duplicate = int(x.duplicated(["transaction_hash", "log_index", "contract"]).sum())
    x = x.drop_duplicates(["transaction_hash", "log_index", "contract"]).sort_values(
        ["block_number", "log_index"]
    )
    x.to_parquet(ROOT / "data/fills.parquet", index=False)
    rows = []
    for r in x.to_dict("records"):
        d = decode_v1_maker(r)
        rows.append(
            {
                **{k: d[k] for k in ["wallet", "token", "side"]},
                "shares": float(d["shares"]),
                "cash": float(d["cash"]),
                "execution_price": float(d["price"]),
                "timestamp": r["timestamp"],
                "block_number": r["block_number"],
                "log_index": r["log_index"],
                "transaction_hash": r["transaction_hash"],
                "exchange_taker": r["taker"] in EXCHANGE,
            }
        )
    f = pd.DataFrame(rows)
    f["fill_only_inventory"] = f.groupby(["wallet", "token"]).shares.cumsum()
    f.to_parquet(ROOT / "data/fill_audit.parquet", index=False)
    src = ROOT.parent / "polymarket/data/gamma/vol10k.jsonl.gz"
    dst = ROOT / "data/raw/gamma_snapshot.jsonl.gz"
    if not dst.exists():
        shutil.copyfile(src, dst)
    catalog = []
    partial = False
    errors = 0
    try:
        with gzip.open(dst, "rt") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    errors += 1
                    continue

                def arr(k):
                    v = r.get(k) or []
                    if isinstance(v, str):
                        try:
                            return json.loads(v)
                        except json.JSONDecodeError:
                            return []
                    return v

                tokens, outs, prices = (
                    arr("clobTokenIds"),
                    arr("outcomes"),
                    arr("outcomePrices"),
                )
                for i, t in enumerate(tokens):
                    catalog.append(
                        {
                            "market": str(r["id"]),
                            "event_id": str(r.get("event_id") or r["id"]),
                            "condition": r.get("conditionId"),
                            "question": r.get("question") or "",
                            "category": category(
                                r.get("question") or "", r.get("tags") or []
                            ),
                            "token": str(t),
                            "outcome_label": str(outs[i]) if i < len(outs) else None,
                            "final_price_metadata": float(prices[i])
                            if i < len(prices)
                            else None,
                            "closed": bool(r.get("closed")),
                            "closed_time_metadata": r.get("closedTime"),
                            "created_time": r.get("createdAt"),
                            "scheduled_end": r.get("endDate"),
                            "neg_risk": bool(r.get("negRisk")),
                        }
                    )
    except (EOFError, OSError):
        partial = True
    c = pd.DataFrame(catalog).drop_duplicates("token", keep="last")
    c.to_parquet(ROOT / "data/market_catalog.parquet", index=False)
    mapped = f.merge(c, on="token", how="left")
    mapped.to_parquet(ROOT / "data/fill_audit_mapped.parquet", index=False)
    audit = {
        "fill_rows": len(f),
        "transactions": int(x.transaction_hash.nunique()),
        "makers": int(f.wallet.nunique()),
        "tokens": int(f.token.nunique()),
        "exchange_taker_rows": int(f.exchange_taker.sum()),
        "negative_fill_only_inventory_rows": int((f.fill_only_inventory < -1e-8).sum()),
        "negative_fill_only_wallet_token_pairs": int(
            f[f.fill_only_inventory < -1e-8].groupby(["wallet", "token"]).ngroups
        ),
        "duplicate_rows": duplicate,
        "start": pd.to_datetime(f.timestamp.min(), unit="s", utc=True).isoformat(),
        "end": pd.to_datetime(f.timestamp.max(), unit="s", utc=True).isoformat(),
        "catalog_tokens": len(c),
        "catalog_markets": int(c.market.nunique()),
        "mapped_rows": int(mapped.market.notna().sum()),
        "mapped_tokens": int(mapped.loc[mapped.market.notna(), "token"].nunique()),
        "gamma_snapshot_truncated": partial,
        "gamma_malformed_lines": errors,
        "gamma_snapshot_sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
        "sample_rule": "All events in first eight monthly V1 partitions: Nov 2022 through Jun 2023; descriptive ledger audit only, not holdout.",
    }
    (ROOT / "data/audit_summary.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
