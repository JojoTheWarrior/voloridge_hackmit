#!/usr/bin/env python3
"""Fetch slices of the NOAA Integrated Surface Database (ISD) from s3://noaa-isd-pds.

Bucket layout (us-east-1, public):
    data/{year}/{USAF}-{WBAN}-{year}.gz   gzipped fixed-width hourly observations
    isd-history.csv                        station metadata (id, name, country, lat/lon, period of record)
    isd-inventory.csv                      per-station per-year observation counts

The full dataset is ~600 GB — always fetch a slice. With no slice args this
script downloads the station metadata files plus one recent year for one
example station (Boston Logan, 725090-14739).

Requires: Python 3.10+, boto3. Uses anonymous S3 access by default
(no credentials needed); pass --signed to use your configured AWS credentials.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET = "noaa-isd-pds"
REGION = "us-east-1"
METADATA_KEYS = ["isd-history.csv", "isd-inventory.csv"]
EXAMPLE_STATION = "725090-14739"  # Boston Logan International Airport
EXAMPLE_YEAR = 2024
# Above this many stations, listing whole year prefixes is cheaper than
# issuing one List request per station.
PER_STATION_LOOKUP_LIMIT = 100


def make_client(signed: bool):
    if signed:
        return boto3.client("s3", region_name=REGION)
    return boto3.client("s3", region_name=REGION, config=Config(signature_version=UNSIGNED))


def parse_years(spec: str) -> list[int]:
    """Parse '2023' or '2020:2023' into a list of years."""
    if ":" in spec:
        lo, hi = spec.split(":", 1)
        start, end = int(lo), int(hi)
        if start > end:
            raise argparse.ArgumentTypeError(f"year range start {start} > end {end}")
        return list(range(start, end + 1))
    return [int(spec)]


def normalize_station(s: str) -> str:
    s = s.strip()
    parts = s.replace("_", "-").split("-")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise argparse.ArgumentTypeError(
            f"station must be 'USAF-WBAN' (e.g. 725090-14739), got: {s!r}"
        )
    usaf, wban = parts
    return f"{usaf.zfill(6)}-{wban.zfill(5)}"


def load_stations_file(path: Path) -> list[str]:
    stations = []
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            stations.append(normalize_station(line))
    return stations


def stations_for_country(s3, country: str) -> list[str]:
    """Filter isd-history.csv by 2-letter FIPS country code (CTRY column)."""
    print(f"Fetching isd-history.csv to resolve stations for country {country!r} ...")
    body = s3.get_object(Bucket=BUCKET, Key="isd-history.csv")["Body"].read()
    reader = csv.DictReader(io.StringIO(body.decode("utf-8", errors="replace")))
    country = country.upper()
    stations = [
        f"{row['USAF']}-{row['WBAN']}"
        for row in reader
        if row.get("CTRY", "").upper() == country
    ]
    print(f"  {len(stations)} stations listed for {country} in isd-history.csv")
    return stations


def list_year_keys(s3, year: int) -> dict[str, int]:
    """List all keys under data/{year}/ -> {key: size}."""
    keys: dict[str, int] = {}
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=f"data/{year}/"):
        for obj in page.get("Contents", []):
            keys[obj["Key"]] = obj["Size"]
    return keys


def resolve_data_keys(s3, years: list[int], stations: list[str] | None) -> dict[str, int]:
    """Resolve the slice to concrete S3 keys with sizes."""
    keys: dict[str, int] = {}
    station_set = set(stations) if stations else None
    for year in years:
        if station_set is not None and len(station_set) <= PER_STATION_LOOKUP_LIMIT:
            # Cheap: one targeted List request per station.
            for st in sorted(station_set):
                resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"data/{year}/{st}-{year}.gz")
                for obj in resp.get("Contents", []):
                    keys[obj["Key"]] = obj["Size"]
        else:
            year_keys = list_year_keys(s3, year)
            if station_set is None:
                keys.update(year_keys)
            else:
                for key, size in year_keys.items():
                    # key = data/{year}/{USAF}-{WBAN}-{year}.gz
                    stem = key.rsplit("/", 1)[-1]
                    station_id = stem.rsplit("-", 1)[0]
                    if station_id in station_set:
                        keys[key] = size
    return keys


def resolve_metadata_keys(s3, names: list[str]) -> dict[str, int]:
    keys = {}
    for name in names:
        try:
            head = s3.head_object(Bucket=BUCKET, Key=name)
            keys[name] = head["ContentLength"]
        except ClientError as exc:
            print(f"warning: could not stat {name}: {exc}", file=sys.stderr)
    return keys


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:,.1f} TB"


def download(s3, keys: dict[str, int], output_dir: Path) -> None:
    total = len(keys)
    total_bytes = sum(keys.values())
    done_bytes = 0
    skipped = 0
    for i, (key, size) in enumerate(sorted(keys.items()), start=1):
        dest = output_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size == size:
            skipped += 1
            done_bytes += size
            print(f"[{i}/{total}] skip (exists) {key}")
            continue
        print(
            f"[{i}/{total}] {key}  {human_bytes(size)}  "
            f"({human_bytes(done_bytes)}/{human_bytes(total_bytes)} done)"
        )
        tmp = dest.with_suffix(dest.suffix + ".part")
        s3.download_file(BUCKET, key, str(tmp))
        tmp.replace(dest)
        done_bytes += size
    print(
        f"Done: {total - skipped} downloaded, {skipped} skipped, "
        f"{human_bytes(total_bytes)} total -> {output_dir}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--output-dir", type=Path, default=Path("./data/noaa_isd"),
        help="local destination directory (default: ./data/noaa_isd)",
    )
    ap.add_argument(
        "--year", type=parse_years, default=None, metavar="YYYY[:YYYY]",
        help="single year (2023) or inclusive range (2020:2023)",
    )
    ap.add_argument(
        "--station", action="append", type=normalize_station, default=None,
        metavar="USAF-WBAN",
        help="station id like 725090-14739; repeatable",
    )
    ap.add_argument(
        "--stations-file", type=Path, default=None,
        help="text file with one USAF-WBAN id per line (# comments allowed)",
    )
    ap.add_argument(
        "--country", default=None, metavar="CC",
        help="2-letter FIPS country code; selects all stations for that country "
             "from isd-history.csv (e.g. US, UK, JA)",
    )
    ap.add_argument(
        "--metadata", action="store_true",
        help="also download isd-history.csv and isd-inventory.csv",
    )
    ap.add_argument(
        "--list", action="store_true",
        help="list matching keys and total size without downloading",
    )
    ap.add_argument(
        "--max-size-gb", type=float, default=5.0,
        help="refuse to download if the slice exceeds this many GB (default: 5)",
    )
    ap.add_argument(
        "--signed", action="store_true",
        help="use configured AWS credentials instead of anonymous access",
    )
    args = ap.parse_args(argv)

    s3 = make_client(args.signed)

    stations: list[str] = []
    if args.station:
        stations.extend(args.station)
    if args.stations_file:
        stations.extend(load_stations_file(args.stations_file))
    if args.country:
        stations.extend(stations_for_country(s3, args.country))
    stations = sorted(set(stations))

    no_slice = not stations and args.year is None
    keys: dict[str, int] = {}

    if no_slice:
        # Safe default: metadata + one recent year for one example station.
        print(
            "No slice args given — fetching station metadata plus "
            f"{EXAMPLE_STATION} (Boston Logan) for {EXAMPLE_YEAR}."
        )
        keys.update(resolve_metadata_keys(s3, METADATA_KEYS))
        keys.update(resolve_data_keys(s3, [EXAMPLE_YEAR], [EXAMPLE_STATION]))
    else:
        if args.metadata:
            keys.update(resolve_metadata_keys(s3, METADATA_KEYS))
        years = args.year if args.year is not None else [EXAMPLE_YEAR]
        if args.year is None:
            print(f"No --year given; defaulting to {EXAMPLE_YEAR}.")
        keys.update(resolve_data_keys(s3, years, stations or None))

    if not keys:
        print("No matching objects found for this slice.", file=sys.stderr)
        return 1

    total_bytes = sum(keys.values())

    if args.list:
        for key, size in sorted(keys.items()):
            print(f"{size:>14,}  s3://{BUCKET}/{key}")
        print(f"\n{len(keys)} objects, {human_bytes(total_bytes)} total")
        return 0

    cap = args.max_size_gb * 1024**3
    if total_bytes > cap:
        print(
            f"Refusing to download: slice is {human_bytes(total_bytes)} which exceeds "
            f"--max-size-gb {args.max_size_gb}. Narrow the slice (fewer years/stations) "
            "or raise the cap.",
            file=sys.stderr,
        )
        return 2

    print(f"Downloading {len(keys)} objects, {human_bytes(total_bytes)} total ...")
    download(s3, keys, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
