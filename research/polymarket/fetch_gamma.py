"""Crawl Polymarket Gamma API (keyless, read-only) via keyset pagination.

Usage: fetch_gamma.py <name> <events|markets> key=value ...
Writes data/gamma/<name>.jsonl.gz (one slim record per market) and is resumable
via data/gamma/<name>.cursor.
"""
import gzip
import json
import sys
import time
from pathlib import Path

import requests

BASE = "https://gamma-api.polymarket.com"
OUT = Path(__file__).parent / "data" / "gamma"
OUT.mkdir(parents=True, exist_ok=True)

MARKET_KEYS = [
    "id", "question", "conditionId", "slug", "endDate", "startDate", "createdAt",
    "closedTime", "closed", "outcomes", "outcomePrices", "volumeNum", "liquidityNum",
    "clobTokenIds", "umaResolutionStatus", "resolutionSource", "groupItemTitle",
    "groupItemThreshold", "negRisk", "description", "bestBid", "bestAsk", "spread",
    "lastTradePrice", "orderPriceMinTickSize", "enableOrderBook", "umaEndDate",
]


def slim_market(m, event=None):
    rec = {k: m.get(k) for k in MARKET_KEYS}
    ev = event or (m.get("events") or [{}])[0]
    rec["event_id"] = ev.get("id")
    rec["event_slug"] = ev.get("slug")
    rec["event_title"] = ev.get("title")
    rec["tags"] = [t.get("slug") for t in (ev.get("tags") or m.get("tags") or [])]
    return rec


def get(session, url, params):
    for attempt in range(8):
        try:
            r = session.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            wait = 2 ** attempt
            print(f"  HTTP {r.status_code}; sleeping {wait}s", flush=True)
        except requests.RequestException as exc:
            wait = 2 ** attempt
            print(f"  {exc!r}; sleeping {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError("gave up")


def main():
    name, kind = sys.argv[1], sys.argv[2]
    params = dict(a.split("=", 1) for a in sys.argv[3:])
    params.setdefault("limit", "100")
    if kind == "markets":
        params.setdefault("include_tag", "true")
    cursor_file = OUT / f"{name}.cursor"
    out_file = OUT / f"{name}.jsonl.gz"
    if cursor_file.exists():
        cursor = cursor_file.read_text().strip()
        if cursor == "DONE":
            print("already done")
            return
        params["after_cursor"] = cursor
    session = requests.Session()
    session.headers["User-Agent"] = "hackathon-research-readonly/0.1"
    n = 0
    with gzip.open(out_file, "at") as fh:
        while True:
            j = get(session, f"{BASE}/{kind}/keyset", params)
            items = j.get(kind, [])
            for it in items:
                if kind == "events":
                    for m in it.get("markets", []):
                        fh.write(json.dumps(slim_market(m, it)) + "\n")
                        n += 1
                else:
                    fh.write(json.dumps(slim_market(it)) + "\n")
                    n += 1
            cursor = j.get("next_cursor")
            if not cursor or not items:
                cursor_file.write_text("DONE")
                break
            fh.flush()
            cursor_file.write_text(cursor)
            params["after_cursor"] = cursor
            if n % 5000 < 100:
                print(f"{name}: {n} markets", flush=True)
            time.sleep(0.15)
    print(f"{name}: finished with {n} markets")


if __name__ == "__main__":
    main()
