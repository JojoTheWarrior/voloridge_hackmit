from __future__ import annotations

import argparse
import csv
import time
from datetime import date, timedelta
from pathlib import Path

import boto3
import pandas as pd
import requests
from botocore import UNSIGNED
from botocore.config import Config

from warsignal.config import OPENALEX_QUERIES
from warsignal.fetch.common import manifest, output_dir, parse_date

def _group_counts(query: str, start: date, end: date):
    base = "https://api.openalex.org/works"
    params = {"filter": f"title_and_abstract.search:{query},from_publication_date:{start},to_publication_date:{end}", "group_by": "publication_date", "per-page": 200, "mailto": "hackmit@example.com"}
    response = requests.get(base, params=params, timeout=60)
    if response.ok:
        groups = response.json().get("group_by", [])
        return [(item["key"], item["count"]) for item in groups], "publication_date"
    rows = []
    current = start.replace(day=1)
    while current <= end:
        month_end = (current.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        lo, hi = max(current, start), min(month_end, end)
        fallback = {"filter": f"title_and_abstract.search:{query},from_publication_date:{lo},to_publication_date:{hi}", "per-page": 1, "mailto": "hackmit@example.com"}
        data = requests.get(base, params=fallback, timeout=60).json()
        rows.append((lo.isoformat(), data.get("meta", {}).get("count", 0)))
        current = month_end + timedelta(days=1)
    return rows, "monthly"

def _download_shard(start: date, end: date):
    client = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))
    candidates = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket="openalex", Prefix="data/parquet/works/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if "updated_date=" not in key or key.split("updated_date=", 1)[1][:10] < "2026-03-01" or obj["Size"] >= 400 * 1024**2:
                continue
            candidates.append(obj)
    if not candidates:
        return None
    obj = min(candidates, key=lambda item: item["Size"])
    path = output_dir("openalex") / "sample" / Path(obj["Key"]).name
    if not path.exists() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file("openalex", obj["Key"], str(path))
        manifest("openalex", f"s3://openalex/{obj['Key']}", obj["Size"], start, end, key=obj["Key"], status="downloaded")
    return path

def fetch(start=date(2025, 3, 1), end=date.today(), quick=False, **_) -> list[Path]:
    items = list(OPENALEX_QUERIES.items())[:5] if quick else list(OPENALEX_QUERIES.items())
    paths = []
    for key, query in items:
        try:
            groups, grouping = _group_counts(query, start, end)
            path = output_dir("openalex") / f"counts_{key}.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle); writer.writerow(["date", "count"]); writer.writerows(groups)
            manifest("openalex", "https://api.openalex.org/works", path.stat().st_size, start, end, query=query, grouping=grouping, status="downloaded")
            paths.append(path)
        except Exception as exc:
            print(f"openalex: {key} failed: {exc}")
        time.sleep(0.2)
    if not quick:
        shard = _download_shard(start, end)
        if shard: paths.append(shard)
    print(f"openalex: {len(paths)} files")
    return paths

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--quick", action="store_true"); a = p.parse_args()
    from warsignal.config import START, END
    fetch(parse_date(a.start) if a.start else START, parse_date(a.end) if a.end else END, quick=a.quick)
