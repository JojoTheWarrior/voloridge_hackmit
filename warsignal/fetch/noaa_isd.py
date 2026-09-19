from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from warsignal.config import STATIONS
from warsignal.fetch.common import cli, manifest, output_dir, retry

def fetch(start=date(2025, 3, 1), end=date.today(), **_) -> list[Path]:
    client = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))
    out = output_dir("noaa_isd")
    years = sorted(set(range(start.year, end.year + 1)) | {2025, 2026})
    tasks = [(slug, station["usaf_wban"], year) for slug, station in STATIONS.items() for year in years]
    def one(task):
        slug, station, year = task
        key = f"data/{year}/{station}-{year}.gz"
        path = out / str(year) / f"{slug}-{station}-{year}.gz"
        if path.exists() and path.stat().st_size > 0:
            return path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            retry(lambda: client.download_file("noaa-isd-pds", key, str(path)))
            size = path.stat().st_size
            manifest("noaa_isd", f"s3://noaa-isd-pds/{key}", size, start, end, key=key, status="downloaded")
            return path
        except Exception as exc:
            manifest("noaa_isd", f"s3://noaa-isd-pds/{key}", 0, start, end, key=key, status="missing", error=str(exc))
            if path.exists():
                path.unlink()
            return None
    paths = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for path in pool.map(one, tasks):
            if path:
                paths.append(path)
    print(f"noaa_isd: {len(paths)} files")
    return paths

if __name__ == "__main__":
    cli(argparse.ArgumentParser(), fetch)
