from __future__ import annotations

import argparse
import csv
import gzip
import json
from datetime import date
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from warsignal.fetch.common import manifest, output_dir, parse_date

BUCKET = "materialsproject-build"
SNAPSHOTS = ("2025-09-25", "2025-02-12")

def _client():
    return boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))

def _objects(client, prefix):
    objects = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix):
        objects.extend(page.get("Contents", []))
    return objects

def _download(client, obj, destination, start, end):
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(BUCKET, obj["Key"], str(destination))
    manifest("materials_project", f"s3://{BUCKET}/{obj['Key']}", obj["Size"], start, end, key=obj["Key"], status="downloaded")
    return destination

def _date_value(value):
    if isinstance(value, dict) and "$date" in value:
        return value["$date"]
    return value

def _build_doc_dates(paths, start, end):
    destination = output_dir("materials_project") / "doc_dates.csv"
    with destination.open("w", newline="", encoding="utf-8") as handle:
        fields = ["snapshot", "collection", "material_id", "created_at", "last_updated", "build_date", "nelements", "chemsys"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for path in paths:
            if path.suffix != ".gz": continue
            parts = path.parts
            try:
                snapshot = parts[-5] if "collections" in parts else ""
                collection = parts[-4]
            except IndexError:
                continue
            with gzip.open(path, "rt", encoding="utf-8") as source:
                for line in source:
                    try: doc = json.loads(line)
                    except json.JSONDecodeError: continue
                    writer.writerow({"snapshot": snapshot, "collection": collection, "material_id": doc.get("material_id"),
                                     "created_at": _date_value(doc.get("created_at")), "last_updated": _date_value(doc.get("last_updated")),
                                     "build_date": _date_value(doc.get("builder_meta", {}).get("build_date") if isinstance(doc.get("builder_meta"), dict) else None),
                                     "nelements": doc.get("nelements"), "chemsys": doc.get("chemsys")})
    manifest("materials_project", "generated:doc_dates.csv", destination.stat().st_size, start, end, status="generated")
    return destination

def fetch(start=date(2025, 3, 1), end=date.today(), quick=False, **_) -> list[Path]:
    client = _client(); paths = []
    snapshots = ["2025-09-25"] if quick else list(SNAPSHOTS)
    for snapshot in snapshots:
        provenance = _objects(client, f"collections/{snapshot}/provenance/")
        materials = _objects(client, f"collections/{snapshot}/materials/")
        if quick:
            materials = sorted(materials, key=lambda obj: obj["Size"])[:10]
        else:
            materials = sorted(materials, key=lambda obj: obj["Size"])[:30]
        for collection, objects in (("provenance", provenance), ("materials", materials)):
            for obj in objects:
                destination = output_dir("materials_project") / obj["Key"]
                paths.append(_download(client, obj, destination, start, end))
    paths.append(_build_doc_dates(paths, start, end))
    print(f"materials_project: {len(paths)} files")
    return paths

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--quick", action="store_true"); a = p.parse_args()
    from warsignal.config import START, END
    fetch(parse_date(a.start) if a.start else START, parse_date(a.end) if a.end else END, quick=a.quick)
