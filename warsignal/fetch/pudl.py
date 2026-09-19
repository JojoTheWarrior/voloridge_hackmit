from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import requests

from warsignal.fetch.common import manifest, output_dir, parse_date

TABLES = ["out_eia923__monthly_fuel_receipts_costs", "out_eia930__hourly_aggregated_demand", "out_eia930__hourly_subregion_demand",
          "out_eia923__monthly_generation_fuel_combined", "core_eia860m__changelog_generators", "out_ferc714__hourly_estimated_state_demand"]

def fetch(start=date(2025, 3, 1), end=date.today(), quick=False, **_) -> list[Path]:
    tables = TABLES[:2] if quick else TABLES
    out = output_dir("pudl"); paths = []
    for table in tables:
        url = f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/stable/{table}.parquet"
        path = out / f"{table}.parquet"
        if path.exists() and path.stat().st_size > 0: paths.append(path); continue
        try:
            head = requests.head(url, timeout=30); head.raise_for_status()
            size = int(head.headers.get("content-length", 0))
            if size > 400 * 1024**2:
                manifest("pudl", url, 0, start, end, status="skipped_too_large", expected_bytes=size); print(f"pudl: skipped {table} ({size} bytes)"); continue
            response = requests.get(url, timeout=300); response.raise_for_status(); path.write_bytes(response.content)
            manifest("pudl", url, len(response.content), start, end, status="downloaded"); paths.append(path)
        except Exception as exc:
            manifest("pudl", url, 0, start, end, status="error", error=str(exc)); print(f"pudl: {table} failed: {exc}")
    print(f"pudl: {len(paths)} files")
    return paths

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--quick", action="store_true"); a = p.parse_args()
    from warsignal.config import START, END
    fetch(parse_date(a.start) if a.start else START, parse_date(a.end) if a.end else END, quick=a.quick)
