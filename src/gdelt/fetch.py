#!/usr/bin/env python3
"""Fetch slices of the GDELT open dataset from s3://gdelt-open-data.

Designed for HackMIT participants running on EC2 (us-east-1) where same-region
S3 access is free, but works anywhere. Anonymous access by default.

Examples:
    python fetch.py --list --start-date 20190415
    python fetch.py --table events --version 2 --start-date 20190401 --end-date 20190402
    python fetch.py --table gkg --start-date 20180101 --list
    python fetch.py --table events --version 1 --start-date 20190901 --end-date 20190905
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKET = "gdelt-open-data"
REGION = "us-east-1"

# Coverage observed in the bucket (dataset is no longer updated).
V1_DAILY_FIRST = date(2013, 4, 1)   # events/YYYYMMDD.export.csv
V1_DAILY_LAST = date(2019, 9, 18)
V2_FIRST = date(2015, 2, 18)        # v2/<table>/YYYYMMDDHHMMSS.<suffix>.csv
V2_LAST = date(2019, 4, 16)

V2_SUFFIX = {"events": "export", "mentions": "mentions", "gkg": "gkg"}

DEFAULT_V2_DAY = "20190415"  # last full day of v2 coverage
DEFAULT_V1_DAY = "20190918"  # last day of v1 coverage


def parse_yyyymmdd(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date {s!r}, expected YYYYMMDD")


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{n} B"


def make_client(signed: bool):
    if signed:
        return boto3.client("s3", region_name=REGION)
    return boto3.client("s3", region_name=REGION, config=Config(signature_version=UNSIGNED))


def day_prefixes(table: str, version: int, start: date, end: date) -> list[str]:
    """One S3 list prefix per day in the range."""
    prefixes = []
    for d in daterange(start, end):
        ymd = d.strftime("%Y%m%d")
        if version == 1:
            prefixes.append(f"events/{ymd}")
        else:
            prefixes.append(f"v2/{table}/{ymd}")
    return prefixes


def list_keys(client, table: str, version: int, start: date, end: date):
    """Yield (key, size) for every matching object."""
    paginator = client.get_paginator("list_objects_v2")
    for prefix in day_prefixes(table, version, start, end):
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                yield obj["Key"], obj["Size"]


def download(client, keys: list[tuple[str, int]], output_dir: Path) -> None:
    total = len(keys)
    total_bytes = sum(s for _, s in keys)
    done_bytes = 0
    skipped = 0
    for i, (key, size) in enumerate(keys, 1):
        dest = output_dir / Path(key).name
        if dest.exists() and dest.stat().st_size == size:
            skipped += 1
            done_bytes += size
            print(f"[{i}/{total}] skip (exists) {dest.name}")
            continue
        print(f"[{i}/{total}] {key} ({human_size(size)}) ...", end=" ", flush=True)
        client.download_file(BUCKET, key, str(dest))
        done_bytes += size
        pct = 100 * done_bytes / total_bytes if total_bytes else 100
        print(f"done  [{human_size(done_bytes)} / {human_size(total_bytes)}, {pct:.0f}%]")
    print(f"\nDownloaded {total - skipped} file(s), skipped {skipped} already present.")
    print(f"Output directory: {output_dir.resolve()}")


def main() -> int:
    p = argparse.ArgumentParser(
        description="Download slices of the GDELT dataset from s3://gdelt-open-data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--output-dir", default="./data/gdelt", help="directory for downloaded files")
    p.add_argument("--table", choices=("events", "mentions", "gkg"), default="events",
                   help="which GDELT table to fetch (mentions/gkg are v2-only)")
    p.add_argument("--version", type=int, choices=(1, 2), default=2, help="GDELT version")
    p.add_argument("--start-date", type=parse_yyyymmdd, default=None, metavar="YYYYMMDD",
                   help="first day of the slice (default: one recent day)")
    p.add_argument("--end-date", type=parse_yyyymmdd, default=None, metavar="YYYYMMDD",
                   help="last day of the slice, inclusive (default: same as start)")
    p.add_argument("--list", action="store_true",
                   help="list matching keys and total size, do not download")
    p.add_argument("--max-size-gb", type=float, default=5.0,
                   help="refuse to download if the slice exceeds this many GB")
    p.add_argument("--signed", action="store_true",
                   help="use default AWS credentials instead of anonymous access")
    args = p.parse_args()

    if args.version == 1 and args.table != "events":
        p.error(f"--table {args.table} is only available in version 2")

    start = args.start_date
    end = args.end_date
    if start is None and end is None:
        start = end = parse_yyyymmdd(DEFAULT_V2_DAY if args.version == 2 else DEFAULT_V1_DAY)
        print(f"No dates given; defaulting to a single recent day: {start:%Y%m%d}")
    elif start is None:
        start = end
    elif end is None:
        end = start
    if end < start:
        p.error("--end-date is before --start-date")

    # Coverage warnings
    if args.version == 2 and (end < V2_FIRST or start > V2_LAST):
        print(f"warning: v2 coverage is {V2_FIRST:%Y%m%d} (23:00 UTC) to {V2_LAST:%Y%m%d}; "
              "your range is outside it", file=sys.stderr)
    if args.version == 1 and (end < V1_DAILY_FIRST or start > V1_DAILY_LAST):
        print(f"warning: v1 daily files cover {V1_DAILY_FIRST:%Y%m%d} to {V1_DAILY_LAST:%Y%m%d} "
              "(earlier data is in yearly/monthly files not handled by this script); "
              "your range is outside it", file=sys.stderr)

    client = make_client(args.signed)
    print(f"Listing s3://{BUCKET} {args.table} v{args.version} "
          f"from {start:%Y%m%d} to {end:%Y%m%d} ...")
    keys = sorted(list_keys(client, args.table, args.version, start, end))
    if not keys:
        print("No matching objects found.", file=sys.stderr)
        return 1

    total_bytes = sum(s for _, s in keys)
    if args.list:
        for key, size in keys:
            print(f"{size:>12}  s3://{BUCKET}/{key}")
        print(f"\n{len(keys)} object(s), total {human_size(total_bytes)}")
        return 0

    cap = args.max_size_gb * 1024 ** 3
    if total_bytes > cap:
        print(f"Refusing to download: slice is {human_size(total_bytes)} which exceeds the "
              f"--max-size-gb cap of {args.max_size_gb} GB. Narrow the date range or raise the cap.",
              file=sys.stderr)
        return 2

    print(f"{len(keys)} object(s), total {human_size(total_bytes)}\n")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    download(client, keys, output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
