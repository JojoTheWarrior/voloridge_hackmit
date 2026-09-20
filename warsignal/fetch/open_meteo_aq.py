from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import requests

from warsignal.config import CITIES, START
from warsignal.fetch.common import manifest, output_dir, parse_date, retry


URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
HOURLY = (
    "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,"
    "sulphur_dioxide,ozone,dust,aerosol_optical_depth"
)


def _request(city, start, end):
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": HOURLY,
        "timezone": "UTC",
    }
    response = retry(lambda: requests.get(URL, params=params, timeout=90), delay=2)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload.get("reason", "Open-Meteo Air Quality error"))
    return payload, response.url, len(response.content)


def fetch(start=START, end=date.today(), **_) -> list[Path]:
    end = min(end, date.today() - timedelta(days=3))
    if end < start:
        return []
    output = output_dir("open_meteo_aq")
    paths = []
    for slug, city in CITIES.items():
        path = output / f"{slug}.json"
        chunks = []
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + timedelta(days=89), end)
            try:
                payload, url, size = _request(city, cursor, chunk_end)
                chunks.append(payload)
                manifest("open_meteo_aq", url, size, cursor, chunk_end, status="downloaded")
            except Exception as exc:
                if chunk_end > cursor:
                    chunk_end = cursor + (chunk_end - cursor) // 2
                    continue
                manifest("open_meteo_aq", URL, 0, cursor, chunk_end, status="error", error=str(exc))
                print(f"open_meteo_aq: {slug} {cursor}..{chunk_end} failed: {exc}")
                chunks = []
                break
            cursor = chunk_end + timedelta(days=1)
        if not chunks:
            continue
        hourly = {"time": []}
        for key in chunks[0].get("hourly", {}):
            hourly[key] = []
        for payload in chunks:
            source = payload.get("hourly", {})
            for key in hourly:
                hourly[key].extend(source.get(key, []))
        combined = {
            "latitude": city["lat"],
            "longitude": city["lon"],
            "timezone": "UTC",
            "hourly": hourly,
        }
        path.write_text(json.dumps(combined), encoding="utf-8")
        paths.append(path)
    print(f"open_meteo_aq: {len(paths)} files")
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    fetch(
        start=parse_date(args.start) if args.start else START,
        end=parse_date(args.end) if args.end else date.today(),
    )
