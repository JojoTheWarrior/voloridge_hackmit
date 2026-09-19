from __future__ import annotations

import json
import math
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import requests

from warsignal.config import DATA_RAW

def date_range(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()

def output_dir(name: str) -> Path:
    path = DATA_RAW / name
    path.mkdir(parents=True, exist_ok=True)
    return path

def manifest_path(name: str) -> Path:
    return output_dir(name) / "_manifest.jsonl"

def manifest(name: str, url: str, size: int, start: date, end: date, **extra: Any) -> None:
    record = {
        "url": url, "key": extra.pop("key", url), "bytes": size,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "requested_start": start.isoformat(), "requested_end": end.isoformat(),
        **extra,
    }
    with manifest_path(name).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")

def retry(operation, attempts: int = 3, delay: float = 1.0):
    error = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(delay * (2 ** attempt))
    raise error

def download_http(name: str, url: str, destination: Path, start: date, end: date, timeout: int = 60) -> Path | None:
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = retry(lambda: requests.get(url, timeout=timeout), delay=1)
        if response.status_code == 404:
            manifest(name, url, 0, start, end, status="missing", http_status=404)
            return None
        response.raise_for_status()
        destination.write_bytes(response.content)
        manifest(name, url, len(response.content), start, end, status="downloaded")
        return destination
    except Exception as exc:
        manifest(name, url, 0, start, end, status="error", error=str(exc))
        print(f"{name}: {url} failed: {exc}")
        return None

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    a = math.sin(math.radians(lat2 - lat1) / 2) ** 2
    a += math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))

def cli(parser, fetcher, quick_handler=None):
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    from warsignal.config import START, END
    start, end = (parse_date(args.start) if args.start else START), (parse_date(args.end) if args.end else END)
    if args.quick and quick_handler:
        start, end, opts = quick_handler(start, end, args)
    else:
        opts = {key: value for key, value in vars(args).items() if key not in {"start", "end"}}
    paths = fetcher(start=start, end=end, **opts)
    print(f"{fetcher.__module__.rsplit('.', 1)[-1]}: {len(paths)} files")
