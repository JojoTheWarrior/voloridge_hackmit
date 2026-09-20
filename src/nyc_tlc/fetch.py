#!/usr/bin/env python3
"""Fetch slices of the NYC TLC Trip Record dataset (s3://nyc-tlc).

Default mode uses signed S3 access via the standard AWS credential chain
(works on HackMIT EC2 instances through the instance IAM role). Use --https
to download anonymously over CloudFront instead (no AWS credentials needed).

NOTE: the nyc-tlc bucket denies ListObjects for everyone, so this script
constructs object keys deterministically and issues per-object HEAD requests
to discover sizes / existence.

Examples:
    python fetch.py --list --type yellow --year 2024 --month 1
    python fetch.py --type green --year 2023 --month 1:3 --zones
    python fetch.py --https --type fhvhv --year 2024 --month 6
    python fetch.py                # one recent month of yellow + zone lookup
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import urllib.error
import urllib.request

BUCKET = "nyc-tlc"
S3_TRIP_PREFIX = "trip data/"  # note: the S3 prefix contains a space
S3_MISC_PREFIX = "misc/"
CLOUDFRONT_BASE = "https://d37ci6vzurychx.cloudfront.net"
CF_TRIP_PREFIX = "trip-data/"  # CloudFront path uses a hyphen instead
CF_MISC_PREFIX = "misc/"

TRIP_TYPES = ("yellow", "green", "fhv", "fhvhv")
ZONE_LOOKUP_FILE = "taxi_zone_lookup.csv"

# First month with data, per TLC publication history.
FIRST_MONTH = {
    "yellow": (2009, 1),
    "green": (2013, 8),
    "fhv": (2015, 1),
    "fhvhv": (2019, 2),
}

CHUNK = 1024 * 256


# --------------------------------------------------------------------------
# CLI parsing
# --------------------------------------------------------------------------

def parse_range(value: str, what: str, lo: int, hi: int) -> list[int]:
    """Parse '2023' or '2023:2024' into an inclusive list of ints."""
    try:
        if ":" in value:
            start_s, end_s = value.split(":", 1)
            start, end = int(start_s), int(end_s)
        else:
            start = end = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid {what} {value!r}: expected N or N:M") from None
    if start > end:
        raise argparse.ArgumentTypeError(f"{what} range {value!r} is reversed")
    for v in (start, end):
        if not lo <= v <= hi:
            raise argparse.ArgumentTypeError(
                f"{what} {v} out of range [{lo}, {hi}]")
    return list(range(start, end + 1))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="With no slice args, downloads one recent month of yellow "
               "trip data plus the taxi zone lookup table.",
    )
    p.add_argument("--output-dir", default="./data/nyc_tlc",
                   help="directory to download into (default: %(default)s)")
    p.add_argument("--type", dest="types", action="append",
                   choices=TRIP_TYPES, metavar="{yellow,green,fhv,fhvhv}",
                   help="trip type; repeatable (default: yellow)")
    p.add_argument("--year", type=lambda v: parse_range(v, "year", 2009, 2100),
                   help="year or range, e.g. 2023 or 2023:2024")
    p.add_argument("--month", type=lambda v: parse_range(v, "month", 1, 12),
                   help="month or range, e.g. 3 or 1:6")
    p.add_argument("--zones", action="store_true",
                   help="also fetch the taxi zone lookup CSV")
    p.add_argument("--list", action="store_true", dest="list_only",
                   help="list matching files and total size, no download")
    p.add_argument("--max-size-gb", type=float, default=5.0,
                   help="refuse to download if the slice exceeds this many "
                        "GB (default: %(default)s)")
    p.add_argument("--https", action="store_true",
                   help="download anonymously over CloudFront (no AWS "
                        "credentials needed) instead of signed S3")
    return p


# --------------------------------------------------------------------------
# Backends: each returns size in bytes or None if the object doesn't exist,
# and can stream an object to a local path.
# --------------------------------------------------------------------------

class HttpsBackend:
    """Anonymous CloudFront access using only the stdlib."""

    name = "CloudFront (anonymous HTTPS)"

    def _url(self, kind: str, filename: str) -> str:
        prefix = CF_TRIP_PREFIX if kind == "trip" else CF_MISC_PREFIX
        return f"{CLOUDFRONT_BASE}/{prefix}{filename}"

    def size(self, kind: str, filename: str) -> int | None:
        req = urllib.request.Request(self._url(kind, filename), method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return int(resp.headers.get("Content-Length", 0))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            raise

    def download(self, kind: str, filename: str, dest: str,
                 progress) -> None:
        with urllib.request.urlopen(self._url(kind, filename),
                                    timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    progress(done, total)


class S3Backend:
    """Signed S3 access via boto3's default credential chain."""

    name = "S3 (signed, default credential chain)"

    def __init__(self):
        try:
            import boto3
        except ImportError:
            sys.exit("boto3 is not installed. Install it with:\n"
                     "  pip3 install boto3\n"
                     "(on Amazon Linux 2023 you may first need: "
                     "sudo dnf install -y python3-pip)\n"
                     "Or re-run with --https to download without boto3.")
        self._client = boto3.client("s3", region_name="us-east-1")

    def _key(self, kind: str, filename: str) -> str:
        prefix = S3_TRIP_PREFIX if kind == "trip" else S3_MISC_PREFIX
        return prefix + filename

    def size(self, kind: str, filename: str) -> int | None:
        from botocore.exceptions import ClientError
        try:
            resp = self._client.head_object(
                Bucket=BUCKET, Key=self._key(kind, filename))
            return resp["ContentLength"]
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "403", "NoSuchKey", "NotFound",
                        "AccessDenied", "Forbidden"):
                # Without ListBucket permission S3 returns 403 for missing
                # keys, so 403 here can mean either "no such file" or "your
                # credentials are not allowed". We surface a hint later.
                return None
            raise

    def download(self, kind: str, filename: str, dest: str,
                 progress) -> None:
        total = self.size(kind, filename) or 0
        done = 0

        def cb(n):
            nonlocal done
            done += n
            progress(done, total)

        self._client.download_file(
            BUCKET, self._key(kind, filename), dest, Callback=cb)


# --------------------------------------------------------------------------
# Slice construction
# --------------------------------------------------------------------------

def latest_probable_month(today: dt.date | None = None) -> list[tuple[int, int]]:
    """Candidate recent (year, month) pairs, newest first.

    TLC publishes with roughly a 2-4 month delay, so probe backwards from
    two months ago until we find one that exists.
    """
    today = today or dt.date.today()
    y, m = today.year, today.month
    candidates = []
    # start two months back, probe up to 12 months
    for _ in range(12):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        candidates.append((y, m))
    return candidates[1:]  # skip last month (almost never published yet)


def month_available(trip_type: str, year: int, month: int) -> bool:
    first = FIRST_MONTH[trip_type]
    return (year, month) >= first


def build_slice(args, backend) -> tuple[list[dict], list[str]]:
    """Return (items, warnings). Each item:
    {kind, filename, size, dest_rel}."""
    items: list[dict] = []
    warnings: list[str] = []

    types = args.types or ["yellow"]
    default_mode = not args.year and not args.month and not args.types \
        and not args.zones

    if args.month and not args.year:
        sys.exit("--month requires --year")

    months: list[tuple[int, int]] = []
    if default_mode:
        # find one recent month of yellow that actually exists
        for y, m in latest_probable_month():
            if backend.size("trip", f"yellow_tripdata_{y:04d}-{m:02d}.parquet"):
                months = [(y, m)]
                break
        if not months:
            sys.exit("could not find a recent yellow month; the data source "
                     "may be unreachable (try --https or check credentials)")
        types = ["yellow"]
    elif args.year:
        month_list = args.month or list(range(1, 13))
        months = [(y, m) for y in args.year for m in month_list]

    for trip_type in types:
        for y, m in months:
            if not month_available(trip_type, y, m):
                warnings.append(
                    f"skipping {trip_type} {y:04d}-{m:02d}: {trip_type} data "
                    f"starts {FIRST_MONTH[trip_type][0]}-"
                    f"{FIRST_MONTH[trip_type][1]:02d}")
                continue
            filename = f"{trip_type}_tripdata_{y:04d}-{m:02d}.parquet"
            size = backend.size("trip", filename)
            if size is None:
                warnings.append(f"not found (or not yet published): {filename}")
                continue
            items.append({"kind": "trip", "filename": filename,
                          "size": size, "dest_rel": filename})

    if args.zones or default_mode:
        size = backend.size("misc", ZONE_LOOKUP_FILE)
        if size is None:
            warnings.append(f"not found: misc/{ZONE_LOOKUP_FILE}")
        else:
            items.append({"kind": "misc", "filename": ZONE_LOOKUP_FILE,
                          "size": size, "dest_rel": ZONE_LOOKUP_FILE})

    return items, warnings


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------

def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def make_progress(label: str):
    def progress(done: int, total: int):
        if total:
            pct = 100 * done / total
            sys.stdout.write(
                f"\r  {label}: {human(done)} / {human(total)} ({pct:.0f}%)")
        else:
            sys.stdout.write(f"\r  {label}: {human(done)}")
        sys.stdout.flush()
    return progress


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    backend = HttpsBackend() if args.https else S3Backend()
    print(f"source: {backend.name}")

    try:
        items, warnings = build_slice(args, backend)
    except Exception as e:  # credential / network problems
        print(f"error querying data source: {e}", file=sys.stderr)
        if not args.https:
            print("hint: if you have no AWS credentials (or they are denied "
                  "by the bucket policy), retry with --https", file=sys.stderr)
        return 1

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    if not items:
        print("no matching files found", file=sys.stderr)
        if not args.https:
            print("hint: the nyc-tlc bucket returns 403 for missing keys AND "
                  "for denied credentials; if you believe the files exist, "
                  "retry with --https", file=sys.stderr)
        return 1

    total_size = sum(i["size"] for i in items)
    print(f"\n{len(items)} file(s), total {human(total_size)}:")
    for i in items:
        print(f"  {i['size']:>13,}  {i['filename']}")

    if args.list_only:
        return 0

    cap_bytes = args.max_size_gb * 1024 ** 3
    if total_size > cap_bytes:
        print(f"\nrefusing to download: slice is {human(total_size)}, "
              f"which exceeds --max-size-gb {args.max_size_gb}. "
              f"Narrow the slice or raise the cap.", file=sys.stderr)
        return 2

    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    print(f"\ndownloading to {out_dir}")

    downloaded = skipped = 0
    for i in items:
        dest = os.path.join(out_dir, i["dest_rel"])
        if os.path.exists(dest) and os.path.getsize(dest) == i["size"]:
            print(f"  skip (already present): {i['filename']}")
            skipped += 1
            continue
        tmp = dest + ".part"
        try:
            backend.download(i["kind"], i["filename"], tmp,
                             make_progress(i["filename"]))
            print()  # newline after progress
            os.replace(tmp, dest)
            downloaded += 1
        except KeyboardInterrupt:
            print("\ninterrupted", file=sys.stderr)
            if os.path.exists(tmp):
                os.remove(tmp)
            return 130
        except Exception as e:
            print(f"\n  failed: {i['filename']}: {e}", file=sys.stderr)
            if os.path.exists(tmp):
                os.remove(tmp)
            return 1

    print(f"\ndone: {downloaded} downloaded, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
