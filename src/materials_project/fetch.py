#!/usr/bin/env python3
"""Fetch slices of the Materials Project open dataset from AWS OpenData S3.

Buckets (us-east-1, public):
  materialsproject-build   build data products (collections of gzipped JSONL)
  materialsproject-parsed  parsed VASP outputs (tasks, charge densities, DOS, ...)
  materialsproject-raw     raw data (manifest only at top level)

Build-bucket layout:
  collections/<YYYY-MM-DD>/<collection>/...   dated snapshots
  e.g. collections/2025-09-25/materials/nelements=3/symmetry_number=12.jsonl.gz

Requires: Python 3.10+, boto3 (pip install boto3). Anonymous access by default.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKETS = ("materialsproject-build", "materialsproject-parsed", "materialsproject-raw")
DEFAULT_BUCKET = "materialsproject-build"
REGION = "us-east-1"

# Small default slice: 1-element materials docs, ~2.7 MB total (~90 files).
DEFAULT_COLLECTION = "materials"
DEFAULT_SUBPREFIX = "nelements=1/"

SNAPSHOT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def make_client(signed: bool):
    if signed:
        return boto3.client("s3", region_name=REGION)
    return boto3.client("s3", region_name=REGION, config=Config(signature_version=UNSIGNED))


def human_size(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TiB"


def list_prefixes(client, bucket: str, prefix: str) -> list[str]:
    """Return common prefixes (i.e. 'subdirectories') directly under `prefix`."""
    out: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            out.append(cp["Prefix"])
    return out


def latest_snapshot(client) -> str:
    """Find the newest dated snapshot under collections/ in the build bucket."""
    dates = []
    for p in list_prefixes(client, DEFAULT_BUCKET, "collections/"):
        name = p[len("collections/"):].rstrip("/")
        if SNAPSHOT_RE.match(name):
            dates.append(name)
    if not dates:
        sys.exit("error: no dated snapshots found under collections/ in the build bucket")
    return max(dates)


def resolve_prefixes(client, args) -> list[str]:
    """Map CLI slice args to a list of S3 key prefixes."""
    if args.prefix:
        return [args.prefix]
    if args.bucket == "materialsproject-build":
        snapshot = args.snapshot or latest_snapshot(client)
        collections = args.collection or [DEFAULT_COLLECTION]
        base = [f"collections/{snapshot}/{c.strip('/')}/" for c in collections]
        # No explicit slice at all -> constrain to a small default partition.
        if not args.collection and args.max_files is None:
            base = [base[0] + DEFAULT_SUBPREFIX]
        return base
    # parsed / raw buckets: collections are top-level prefixes
    if args.collection:
        return [f"{c.strip('/')}/" for c in args.collection]
    sys.exit(
        f"error: for bucket {args.bucket} pass --collection or --prefix "
        "(use --list-collections to see what is available)"
    )


def iter_objects(client, bucket: str, prefix: str):
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Size"] == 0 and obj["Key"].endswith("/"):
                continue  # directory marker
            yield obj


def collect_slice(client, bucket: str, prefixes: list[str], max_files: int | None):
    objects = []
    for prefix in prefixes:
        count = 0
        for obj in iter_objects(client, bucket, prefix):
            objects.append(obj)
            count += 1
            if max_files is not None and count >= max_files:
                break
    return objects


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Download slices of the Materials Project AWS OpenData buckets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--output-dir", default="./data/materials_project",
                    help="local directory to download into")
    ap.add_argument("--bucket", choices=BUCKETS, default=DEFAULT_BUCKET,
                    help="source bucket")
    ap.add_argument("--collection", action="append", metavar="NAME",
                    help="collection to fetch (repeatable), e.g. materials, thermo, "
                         "summary, elasticity, dielectric ... (see --list-collections)")
    ap.add_argument("--snapshot", metavar="YYYY-MM-DD",
                    help="build-bucket snapshot date (default: newest available)")
    ap.add_argument("--prefix",
                    help="free-form S3 key prefix override (relative to bucket root); "
                         "wins over --collection/--snapshot")
    ap.add_argument("--max-files", type=int, default=None,
                    help="cap on number of files per collection/prefix")
    ap.add_argument("--max-size-gb", type=float, default=5.0,
                    help="refuse to download if the slice exceeds this many GB")
    ap.add_argument("--list", action="store_true",
                    help="list matching keys and total size without downloading")
    ap.add_argument("--list-collections", action="store_true",
                    help="enumerate top-level collections in the chosen bucket and exit")
    ap.add_argument("--signed", action="store_true",
                    help="use default AWS credentials instead of anonymous access")
    args = ap.parse_args()

    client = make_client(args.signed)

    if args.list_collections:
        if args.bucket == "materialsproject-build":
            snapshot = args.snapshot or latest_snapshot(client)
            print(f"Collections in {args.bucket} (snapshot {snapshot}):")
            root = f"collections/{snapshot}/"
        else:
            print(f"Top-level prefixes in {args.bucket}:")
            root = ""
        for p in list_prefixes(client, args.bucket, root):
            name = p[len(root):].rstrip("/")
            if name:
                print(f"  {name}")
        return

    prefixes = resolve_prefixes(client, args)
    print(f"bucket:   s3://{args.bucket}")
    for p in prefixes:
        print(f"prefix:   {p}")

    objects = collect_slice(client, args.bucket, prefixes, args.max_files)
    total = sum(o["Size"] for o in objects)
    print(f"matched:  {len(objects)} files, {human_size(total)}")

    if args.list:
        for o in objects:
            print(f"  {human_size(o['Size']):>12}  {o['Key']}")
        return

    if not objects:
        sys.exit("error: no objects matched this slice")

    cap = args.max_size_gb * 1024**3
    if total > cap:
        sys.exit(
            f"error: slice is {human_size(total)}, exceeds --max-size-gb={args.max_size_gb}. "
            "Narrow the slice (--prefix / --max-files) or raise the cap."
        )

    out_root = Path(args.output_dir)
    downloaded = skipped = 0
    done_bytes = 0
    for i, obj in enumerate(objects, 1):
        key, size = obj["Key"], obj["Size"]
        dest = out_root / args.bucket / key
        if dest.exists() and dest.stat().st_size == size:
            skipped += 1
            done_bytes += size
            print(f"[{i}/{len(objects)}] skip (exists)  {key}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{i}/{len(objects)}] {human_size(size):>10}  {key}", flush=True)
        client.download_file(args.bucket, key, str(dest))
        downloaded += 1
        done_bytes += size
        pct = 100 * done_bytes / total if total else 100
        print(f"          -> {dest}  ({human_size(done_bytes)} / {human_size(total)}, {pct:.0f}%)")

    print(f"done: {downloaded} downloaded, {skipped} skipped, "
          f"{human_size(total)} total -> {out_root.resolve()}")


if __name__ == "__main__":
    main()
