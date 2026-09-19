from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

from warsignal.fetch.common import cli, date_range, download_http, output_dir

BASE = "https://data.gdeltproject.org"

def v1_url(day: date) -> str:
    return f"{BASE}/events/{day:%Y%m%d}.export.CSV.zip"

def v2_url(day: date, hour: int, kind: str = "gkg") -> str:
    stamp = f"{day:%Y%m%d}{hour:02d}0000"
    suffix = "gkg.csv.zip" if kind == "gkg" else "export.CSV.zip"
    return f"{BASE}/gdeltv2/{stamp}.{suffix}"

def fetch(start=date(2025, 3, 1), end=date.today(), gkg_per_day=4, quick=False, **_) -> list[Path]:
    if quick:
        start, end = date(2026, 2, 21), date(2026, 3, 7)
    tasks = []
    for day in date_range(start, end):
        tasks.append((day, v1_url(day), output_dir("gdelt_live") / "v1" / f"{day:%Y%m%d}.export.CSV.zip", "v1"))
        for hour in (0, 6, 12, 18)[:int(gkg_per_day)]:
            tasks.append((day, v2_url(day, hour), output_dir("gdelt_live") / "v2_gkg" / f"{day:%Y%m%d}{hour:02d}0000.gkg.csv.zip", "gkg"))
    def one(task):
        day, url, path, kind = task
        return download_http("gdelt_live", url, path, start, end, timeout=120)
    paths = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for path in pool.map(one, tasks):
            if path:
                paths.append(path)
    # Export files are only added where the daily v1 file was missing.
    missing_days = {day for day, _, path, _ in tasks if path.parent.name == "v1" and not path.exists()}
    export_tasks = [(day, v2_url(day, hour, "export"), output_dir("gdelt_live") / "v2_export" / f"{day:%Y%m%d}{hour:02d}0000.export.CSV.zip")
                    for day in missing_days for hour in (0, 6, 12, 18)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for path in pool.map(lambda t: download_http("gdelt_live", t[1], t[2], start, end, timeout=120), export_tasks):
            if path:
                paths.append(path)
    print(f"gdelt_live: {len(paths)} files requested")
    return paths

if __name__ == "__main__":
    cli(argparse.ArgumentParser(), fetch)
