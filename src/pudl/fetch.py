#!/usr/bin/env python3
"""Fetch slices of the PUDL (Public Utility Data Liberation) dataset from S3.

Bucket: s3://pudl.catalyst.coop (public, us-west-2)

Each release prefix (stable/, nightly/, vYYYY.M.N/) contains one Apache
Parquet file per table, named <table_name>.parquet, directly under the
release prefix. Anonymous access is used by default; pass --signed to use
your default AWS credentials (e.g. the EC2 instance IAM role).

Examples:
    python fetch.py                                  # small default sample
    python fetch.py --list-tables                    # enumerate tables in release
    python fetch.py --table core_eia__entity_plants  # exact table
    python fetch.py --table ferc1 --list             # preview a substring match
    python fetch.py --release v2026.8.0 --table core_eia860__scd_plants
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKET = "pudl.catalyst.coop"
BUCKET_REGION = "us-west-2"
DEFAULT_RELEASE = "stable"
DEFAULT_OUTPUT_DIR = "./data/pudl"
DEFAULT_MAX_SIZE_GB = 5.0

# Small, broadly useful sample downloaded when no slice args are given.
DEFAULT_SAMPLE_TABLES = [
    "core_eia__entity_plants",     # ~1.3 MB: one row per EIA plant
    "core_eia__entity_utilities",  # ~0.4 MB: one row per EIA utility
    "core_eia__entity_generators", # ~0.5 MB: one row per EIA generator
]


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} TB"


def make_client(signed: bool):
    if signed:
        return boto3.client("s3", region_name=BUCKET_REGION)
    return boto3.client(
        "s3", region_name=BUCKET_REGION, config=Config(signature_version=UNSIGNED)
    )


def list_release_tables(client, release: str) -> dict[str, dict]:
    """Return {table_name: {"key": ..., "size": ...}} for parquet files
    directly under the release prefix (subprefixes like ferc1_dbf/ skipped)."""
    prefix = f"{release}/"
    tables: dict[str, dict] = {}
    paginator = client.get_paginator("list_objects_v2")
    found_anything = False
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix, Delimiter="/"):
        if page.get("Contents") or page.get("CommonPrefixes"):
            found_anything = True
        for obj in page.get("Contents", []):
            key = obj["Key"]
            name = key[len(prefix):]
            if "/" in name or not name.endswith(".parquet"):
                continue
            tables[name[: -len(".parquet")]] = {"key": key, "size": obj["Size"]}
    if not found_anything:
        sys.exit(
            f"error: release '{release}' not found in s3://{BUCKET}/. "
            "Try 'stable', 'nightly', or a pinned version like 'v2026.8.0'."
        )
    return tables


def match_tables(tables: dict[str, dict], patterns: list[str]) -> dict[str, dict]:
    """Exact table-name match first; otherwise case-insensitive substring."""
    matched: dict[str, dict] = {}
    for pat in patterns:
        if pat in tables:
            matched[pat] = tables[pat]
            continue
        subs = {n: m for n, m in tables.items() if pat.lower() in n.lower()}
        if not subs:
            print(f"warning: no table matches '{pat}'", file=sys.stderr)
        matched.update(subs)
    return matched


def download(client, selection: dict[str, dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(selection)
    for i, (name, meta) in enumerate(sorted(selection.items()), 1):
        dest = output_dir / f"{name}.parquet"
        if dest.exists() and dest.stat().st_size == meta["size"]:
            print(f"[{i}/{total}] skip (already downloaded): {dest.name}")
            continue
        print(f"[{i}/{total}] downloading {meta['key']} ({human_size(meta['size'])}) ...")
        done = 0
        last_pct = -1

        def progress(chunk: int) -> None:
            nonlocal done, last_pct
            done += chunk
            pct = int(done * 100 / meta["size"]) if meta["size"] else 100
            if pct >= last_pct + 10:
                last_pct = pct
                print(f"    {pct}% ({human_size(done)})", flush=True)

        client.download_file(BUCKET, meta["key"], str(dest), Callback=progress)
        print(f"    saved -> {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download per-table Parquet slices of the PUDL dataset "
        f"from s3://{BUCKET}.",
        epilog="Default (no slice args): downloads a small sample of entity "
        f"tables ({', '.join(DEFAULT_SAMPLE_TABLES)}). Never downloads a "
        "whole release.",
    )
    parser.add_argument(
        "--output-dir", default=DEFAULT_OUTPUT_DIR,
        help=f"directory for downloaded files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--release", default=DEFAULT_RELEASE,
        help="release prefix: 'stable' (default), 'nightly', or a pinned "
        "version like 'v2026.8.0'",
    )
    parser.add_argument(
        "--table", action="append", default=None, metavar="NAME",
        help="table to fetch; exact name (e.g. core_eia__entity_plants) or "
        "substring (e.g. ferc1). Repeatable.",
    )
    parser.add_argument(
        "--list-tables", action="store_true",
        help="list all tables available in the release and exit",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="list keys and total size for the selected slice without downloading",
    )
    parser.add_argument(
        "--max-size-gb", type=float, default=DEFAULT_MAX_SIZE_GB,
        help=f"refuse to download a slice larger than this (default: {DEFAULT_MAX_SIZE_GB})",
    )
    parser.add_argument(
        "--signed", action="store_true",
        help="use default AWS credentials instead of anonymous access",
    )
    args = parser.parse_args()

    client = make_client(args.signed)
    tables = list_release_tables(client, args.release)

    if args.list_tables:
        for name in sorted(tables):
            print(f"{human_size(tables[name]['size']):>12}  {name}")
        print(f"\n{len(tables)} tables in release '{args.release}'")
        return

    patterns = args.table if args.table else DEFAULT_SAMPLE_TABLES
    if not args.table:
        print("no --table given; selecting small default sample: "
              + ", ".join(DEFAULT_SAMPLE_TABLES))

    selection = match_tables(tables, patterns)
    if not selection:
        sys.exit("error: no tables matched. Use --list-tables to see what exists.")

    total_size = sum(m["size"] for m in selection.values())

    if args.list:
        for name in sorted(selection):
            print(f"{human_size(selection[name]['size']):>12}  s3://{BUCKET}/{selection[name]['key']}")
        print(f"\n{len(selection)} files, total {human_size(total_size)}")
        return

    cap_bytes = args.max_size_gb * 1024**3
    if total_size > cap_bytes:
        sys.exit(
            f"error: selected slice is {human_size(total_size)}, which exceeds "
            f"the --max-size-gb cap of {args.max_size_gb} GB. Narrow your "
            "--table patterns (check with --list) or raise --max-size-gb.\n"
            "Note: core_epacems__hourly_emissions alone is ~4.9 GB."
        )

    print(f"slice: {len(selection)} files, total {human_size(total_size)}")
    download(client, selection, Path(args.output_dir))
    print("done.")


if __name__ == "__main__":
    main()
