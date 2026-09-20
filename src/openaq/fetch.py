#!/usr/bin/env python3
"""Fetch slices of the OpenAQ data archive from S3.

Bucket: s3://openaq-data-archive (us-east-1)
Layout: records/csv.gz/locationid={id}/year={YYYY}/month={MM}/location-{id}-{YYYYMMDD}.csv.gz

Anonymous (unsigned) access by default; pass --signed to use the default
AWS credential chain (e.g. the instance IAM role on EC2).

Requires: Python 3.10+, boto3 (pip3 install boto3).
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
except ImportError:
    sys.exit(
        "boto3 is required. On Amazon Linux 2023:\n"
        "  sudo dnf install -y python3-pip && pip3 install boto3"
    )

BUCKET = "openaq-data-archive"
REGION = "us-east-1"
BASE_PREFIX = "records/csv.gz/"
DEFAULT_LOCATION_ID = 2178  # Del Norte, Albuquerque NM - small, long-running station

KEY_RE = re.compile(
    r"records/csv\.gz/locationid=(?P<loc>\d+)/year=(?P<year>\d{4})/month=(?P<month>\d{2})/"
    r"location-\d+-\d{8}\.csv\.gz$"
)


def parse_int_range(text: str, name: str) -> list[int]:
    """Parse '3', '1:6', or comma lists like '1,3,5:7' into a sorted int list."""
    values: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            lo_s, _, hi_s = part.partition(":")
            try:
                lo, hi = int(lo_s), int(hi_s)
            except ValueError:
                raise argparse.ArgumentTypeError(f"invalid {name} range: {part!r}")
            if lo > hi:
                raise argparse.ArgumentTypeError(f"{name} range start > end: {part!r}")
            values.update(range(lo, hi + 1))
        else:
            try:
                values.add(int(part))
            except ValueError:
                raise argparse.ArgumentTypeError(f"invalid {name}: {part!r}")
    return sorted(values)


def default_year_month() -> tuple[int, int]:
    """The most recent full month (archive files land ~72h after end of day)."""
    today = dt.date.today()
    first_of_month = today.replace(day=1)
    prev_month_end = first_of_month - dt.timedelta(days=5)
    return prev_month_end.year, prev_month_end.month


def build_prefixes(location_ids: list[int], years: list[int] | None, months: list[int] | None) -> list[str]:
    """Build the narrowest possible S3 prefixes for the requested slice."""
    prefixes = []
    for loc in location_ids:
        loc_prefix = f"{BASE_PREFIX}locationid={loc}/"
        if not years:
            prefixes.append(loc_prefix)  # filter months later, if any
            continue
        for year in years:
            year_prefix = f"{loc_prefix}year={year}/"
            if not months:
                prefixes.append(year_prefix)
                continue
            for month in months:
                prefixes.append(f"{year_prefix}month={month:02d}/")
    return prefixes


def list_matching_objects(s3, prefixes: list[str], months: list[int] | None, years: list[int] | None):
    """Yield (key, size) for objects matching the slice, filtering partitions the prefix couldn't."""
    paginator = s3.get_paginator("list_objects_v2")
    for prefix in prefixes:
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                m = KEY_RE.search(obj["Key"])
                if not m:
                    continue
                if years and int(m.group("year")) not in years:
                    continue
                if months and int(m.group("month")) not in months:
                    continue
                yield obj["Key"], obj["Size"]


def human_size(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TiB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download slices of the OpenAQ S3 archive (s3://openaq-data-archive).",
        epilog="With no slice args, downloads one small default slice: "
        f"location {DEFAULT_LOCATION_ID}, most recent full month.",
    )
    parser.add_argument("--output-dir", default="./data/openaq", help="download destination (default: ./data/openaq)")
    parser.add_argument(
        "--location-id", action="append", type=int, metavar="ID",
        help="OpenAQ location id; repeatable (e.g. --location-id 2178 --location-id 8118)",
    )
    parser.add_argument("--year", metavar="YYYY[:YYYY]", help="year or inclusive range, e.g. 2023 or 2023:2024")
    parser.add_argument("--month", metavar="M[:M]", help="month or inclusive range, e.g. 2 or 1:6")
    parser.add_argument("--list", action="store_true", help="list matching keys and total size; no download")
    parser.add_argument("--max-size-gb", type=float, default=5.0, help="refuse to download slices larger than this (default: 5)")
    parser.add_argument("--signed", action="store_true", help="use default AWS credentials instead of anonymous access")
    args = parser.parse_args()

    years = parse_int_range(args.year, "year") if args.year else None
    months = parse_int_range(args.month, "month") if args.month else None

    if args.location_id:
        location_ids = sorted(set(args.location_id))
    else:
        location_ids = [DEFAULT_LOCATION_ID]
        if years is None and months is None:
            dy, dm = default_year_month()
            years, months = [dy], [dm]
            print(f"No slice args given; defaulting to location {DEFAULT_LOCATION_ID}, {dy}-{dm:02d}.")
        else:
            print(f"No --location-id given; defaulting to location {DEFAULT_LOCATION_ID}.")

    if args.signed:
        s3 = boto3.client("s3", region_name=REGION)
    else:
        s3 = boto3.client("s3", region_name=REGION, config=Config(signature_version=UNSIGNED))

    prefixes = build_prefixes(location_ids, years, months)
    print(f"Scanning {len(prefixes)} prefix(es) under s3://{BUCKET}/{BASE_PREFIX} ...")

    objects = sorted(list_matching_objects(s3, prefixes, months, years))
    total_size = sum(size for _, size in objects)

    if not objects:
        print("No objects match this slice. Check location id / year / month (data may not exist).")
        return 1

    if args.list:
        for key, size in objects:
            print(f"{size:>12}  s3://{BUCKET}/{key}")
        print(f"\n{len(objects)} object(s), total {human_size(total_size)}")
        return 0

    max_bytes = args.max_size_gb * 1024**3
    if total_size > max_bytes:
        print(
            f"Refusing to download: slice is {human_size(total_size)} across {len(objects)} files, "
            f"which exceeds --max-size-gb {args.max_size_gb}. Narrow the slice or raise the cap."
        )
        return 2

    out_root = Path(args.output_dir)
    print(f"Downloading {len(objects)} file(s), {human_size(total_size)} -> {out_root}")

    downloaded = skipped = 0
    done_bytes = 0
    for i, (key, size) in enumerate(objects, 1):
        dest = out_root / Path(key)
        if dest.exists() and dest.stat().st_size == size:
            skipped += 1
            done_bytes += size
            print(f"[{i}/{len(objects)}] skip (exists) {dest.name}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(BUCKET, key, str(dest))
        downloaded += 1
        done_bytes += size
        pct = 100 * done_bytes / total_size if total_size else 100
        print(f"[{i}/{len(objects)}] {dest.name} ({human_size(size)}) - {pct:.0f}%")

    print(f"Done: {downloaded} downloaded, {skipped} skipped, {human_size(total_size)} total in {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
