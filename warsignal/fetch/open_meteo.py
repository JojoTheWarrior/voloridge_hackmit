from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path

import requests

from warsignal.config import CITIES
from warsignal.fetch.common import manifest, output_dir, retry, parse_date

def fetch(start=date(2025, 3, 1), end=date.today(), **_) -> list[Path]:
    paths = []
    for slug, city in CITIES.items():
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {"latitude": city["lat"], "longitude": city["lon"], "start_date": start.isoformat(), "end_date": end.isoformat(),
                  "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,shortwave_radiation_sum", "timezone": "UTC"}
        path = output_dir("open_meteo") / f"{slug}.json"
        if path.exists() and path.stat().st_size > 0:
            try:
                existing = json.loads(path.read_text(encoding="utf-8")).get("daily", {}).get("time", [])
                if existing and existing[0] <= start.isoformat() and existing[-1] >= end.isoformat():
                    paths.append(path)
                    continue
            except (OSError, ValueError, TypeError):
                pass
        try:
            response = retry(lambda: requests.get(url, params=params, timeout=60))
            response.raise_for_status()
            path.write_bytes(response.content)
            manifest("open_meteo", response.url, len(response.content), start, end, status="downloaded")
            paths.append(path)
        except Exception as exc:
            manifest("open_meteo", url, 0, start, end, status="error", error=str(exc))
            print(f"open_meteo: {slug} failed: {exc}")
        time.sleep(1)
    print(f"open_meteo: {len(paths)} files")
    return paths

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--quick", action="store_true")
    args = p.parse_args()
    from warsignal.config import START, END
    start = parse_date(args.start) if args.start else START
    end = parse_date(args.end) if args.end else END
    if args.quick: start, end = date(2026, 2, 21), date(2026, 3, 7)
    fetch(start, end)
