from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta

import requests

from warsignal.config import START
from warsignal.fetch.common import manifest, parse_date, output_dir


TOPICS = {
    "tungsten": "tungsten",
    "lithium": "lithium",
    "rare_earth": "rare earth",
    "hormuz": "strait of hormuz",
    "iran": "iran",
    "lng": "liquefied natural gas",
    "hydrogen": "hydrogen",
    "drone": "drone",
    "sanctions": "sanctions",
    "oil_price": "oil price",
    "solar": "photovoltaic",
    "nuclear": "uranium enrichment",
    "missile": "missile",
    "desalination": "desalination",
    "shipping": "maritime shipping",
    "cybersecurity": "cybersecurity",
    "graphite": "graphite",
    "uranium": "uranium",
    "ammonia": "ammonia",
    "battery": "battery",
}

START_WEEK = date(2025, 3, 3)
API_URL = "https://api.crossref.org/works"
MAILTO = "warsignal@example.com"


def _weeks(start: date, end: date):
    first = max(START_WEEK, start)
    first += timedelta(days=(7 - first.weekday()) % 7)
    last = end - timedelta(days=end.weekday())
    current = first
    while current <= last:
        yield current
        current += timedelta(days=7)


def _count(session, query, week_start, week_end):
    params = {
        "filter": (
            f"from-created-date:{week_start.isoformat()},"
            f"until-created-date:{week_end.isoformat()}"
        ),
        "rows": 0,
        "mailto": MAILTO,
    }
    if query:
        params["query"] = query
    response = session.get(API_URL, params=params, timeout=60)
    if response.status_code == 429 or response.status_code >= 500:
        raise requests.HTTPError(f"Crossref transient HTTP {response.status_code}", response=response)
    response.raise_for_status()
    return int(response.json()["message"]["total-results"]), response


def _request_with_backoff(session, query, week_start, week_end):
    error = None
    for attempt in range(5):
        try:
            return _count(session, query, week_start, week_end)
        except (requests.RequestException, ValueError, KeyError) as exc:
            error = exc
            if attempt == 4:
                raise
            retry_after = 0.0
            response = getattr(exc, "response", None)
            if response is not None:
                try:
                    retry_after = float(response.headers.get("Retry-After", 0))
                except (TypeError, ValueError):
                    retry_after = 0.0
            time.sleep(max(retry_after, 1.0 * (2 ** attempt)))
    raise error


def _topic_path(topic):
    return output_dir("crossref") / f"{topic}.json"


def _load_counts(topic):
    path = _topic_path(topic)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {str(key): int(value) for key, value in payload.items()}
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {}


def fetch(start=START, end=date.today(), **_):
    weeks = list(_weeks(start, end))
    output_dir("crossref")
    session = requests.Session()
    session.headers.update({"User-Agent": f"WarSignal/1.0 (mailto:{MAILTO})"})
    summaries = {}
    for topic, query in {"all": None, **TOPICS}.items():
        counts = _load_counts(topic)
        failures = []
        for week_start in weeks:
            key = week_start.isoformat()
            if key in counts:
                continue
            week_end = week_start + timedelta(days=6)
            try:
                value, response = _request_with_backoff(session, query, week_start, week_end)
                counts[key] = value
                manifest(
                    "crossref",
                    response.url,
                    len(response.content),
                    week_start,
                    week_end,
                    status="downloaded",
                    topic=topic,
                    query=query,
                )
            except Exception as exc:
                failures.append(key)
                manifest(
                    "crossref",
                    API_URL,
                    0,
                    week_start,
                    week_end,
                    status="error",
                    topic=topic,
                    query=query,
                    error=str(exc),
                )
            finally:
                time.sleep(0.15)
            _topic_path(topic).write_text(
                json.dumps(dict(sorted(counts.items())), indent=2),
                encoding="utf-8",
            )
        _topic_path(topic).write_text(
            json.dumps(dict(sorted(counts.items())), indent=2),
            encoding="utf-8",
        )
        summaries[topic] = {"weeks": len(counts), "failures": failures}
        print(f"{topic}: {len(counts)} weeks, failures={len(failures)}", flush=True)
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    fetch(
        start=parse_date(args.start) if args.start else START,
        end=parse_date(args.end) if args.end else date.today(),
    )
