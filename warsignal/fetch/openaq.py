from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import boto3
import requests
from botocore import UNSIGNED
from botocore.config import Config

from warsignal.config import CITIES, env
from warsignal.fetch.common import date_range, haversine_km, manifest, output_dir, parse_date

BUCKET = "openaq-data-archive"
ROOT = "records/csv.gz/"

def _s3():
    return boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))

def _first_2026(client, location_id: str):
    response = client.list_objects_v2(Bucket=BUCKET, Prefix=f"{ROOT}locationid={location_id}/year=2026/", MaxKeys=1)
    return (response.get("Contents") or [None])[0]

def build_index(max_ids: int = 4000, start: date = date(2025, 3, 1), end: date = date.today()) -> Path:
    out = output_dir("openaq")
    index = out / "location_index.csv"
    existing = set()
    if index.exists():
        with index.open(newline="", encoding="utf-8") as handle:
            existing = {row["id"] for row in csv.DictReader(handle)}
    client = _s3()
    ids = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=ROOT, Delimiter="/"):
        for prefix in page.get("CommonPrefixes", []):
            marker = "locationid="
            if marker not in prefix["Prefix"]:
                continue
            value = prefix["Prefix"].split(marker, 1)[1].strip("/")
            if value.isdigit() and value not in existing:
                ids.append(value)
                if len(ids) >= max_ids:
                    break
        if len(ids) >= max_ids:
            break
    def inspect(location_id):
        obj = _first_2026(client, location_id)
        if not obj:
            return None
        try:
            raw = client.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read()
            row = next(csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8", "replace"))))
            return {"id": location_id, "name": row.get("location", ""), "lat": row.get("lat", ""), "lon": row.get("lon", ""), "first_file": obj["Key"]}
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=32) as pool:
        rows = [row for row in pool.map(inspect, ids) if row]
    write_header = not index.exists() or index.stat().st_size == 0
    with index.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "name", "lat", "lon", "first_file"])
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    print(f"openaq: indexed {len(rows)} locations")
    return index

def _api_locations():
    key = env("OPENAQ_API_KEY")
    if not key:
        return []
    headers = {"X-API-Key": key}
    locations = []
    for slug, city in CITIES.items():
        response = requests.get("https://api.openaq.org/v3/locations", params={"coordinates": f"{city['lat']},{city['lon']}", "radius": 25000, "limit": 100}, headers=headers, timeout=60)
        response.raise_for_status()
        for item in response.json().get("results", []):
            item["city_slug"] = slug
            locations.append(item)
    path = output_dir("openaq") / "locations.json"
    path.write_text(json.dumps(locations, indent=2), encoding="utf-8")
    return locations

def fetch(start=date(2025, 3, 1), end=date.today(), max_ids=4000, quick=False, **_) -> list[Path]:
    if quick:
        max_ids = min(int(max_ids), 300)
    if env("OPENAQ_API_KEY"):
        locations = _api_locations()
        rows = [{"id": str(item["id"]), "name": item.get("name", ""), "lat": item.get("coordinates", {}).get("latitude"), "lon": item.get("coordinates", {}).get("longitude")} for item in locations]
    else:
        index = build_index(int(max_ids), start, end)
        with index.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    matched = []
    for row in rows:
        try:
            lat, lon = float(row["lat"]), float(row["lon"])
        except (ValueError, TypeError):
            continue
        cities = [slug for slug, city in CITIES.items() if haversine_km(lat, lon, city["lat"], city["lon"]) <= 50]
        if cities:
            row["cities"] = cities
            matched.append(row)
    paths = []
    client = _s3()
    for row in matched:
        location_id = row["id"]
        for day in date_range(start, end):
            key = f"{ROOT}locationid={location_id}/year={day.year}/month={day.month:02d}/"
            prefix_response = client.list_objects_v2(Bucket=BUCKET, Prefix=key)
            for item in prefix_response.get("Contents", []):
                destination = output_dir("openaq") / item["Key"]
                if destination.exists() and destination.stat().st_size > 0:
                    paths.append(destination)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                try:
                    client.download_file(BUCKET, item["Key"], str(destination))
                    manifest("openaq", f"s3://{BUCKET}/{item['Key']}", item["Size"], start, end, key=item["Key"], status="downloaded")
                    paths.append(destination)
                except Exception as exc:
                    manifest("openaq", f"s3://{BUCKET}/{item['Key']}", 0, start, end, key=item["Key"], status="error", error=str(exc))
    print(f"openaq: {len(matched)} locations matched, {len(paths)} files")
    return paths

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--max-ids", type=int, default=4000); p.add_argument("--quick", action="store_true"); a = p.parse_args()
    from warsignal.config import START, END
    start = parse_date(a.start) if a.start else START; end = parse_date(a.end) if a.end else END
    fetch(start, end, max_ids=a.max_ids, quick=a.quick)
