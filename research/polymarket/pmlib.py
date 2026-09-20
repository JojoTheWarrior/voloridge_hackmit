"""Shared helpers: tolerant jsonl.gz reader, cached HTTP GET with backoff."""
import gzip
import hashlib
import json
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).parent
DATA = ROOT / "data"
_session = requests.Session()
_session.headers["User-Agent"] = "hackathon-research-readonly/0.1"


def cached_response(url, params=None, cache_dir="responses", retries=5, timeout=60, read_batch=None):
    """Auditable binary GET cache, including negative responses; never sends credentials.

    Separate from legacy JSON cache so existing caches remain usable. Sequential callers
    pause 0.5 s and honor Retry-After on 429/5xx. Metadata contains no private headers.
    """
    if read_batch is not None:
        assert url == 'https://clob.polymarket.com/batch-prices-history', 'Only documented read-only batch retrieval is permitted'
    key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True) +
                          (json.dumps(read_batch,sort_keys=True) if read_batch is not None else '')).encode()).hexdigest()
    d = DATA / cache_dir
    d.mkdir(parents=True, exist_ok=True)
    meta, body = d / (key + '.json'), d / (key + '.bin')
    if meta.exists() and body.exists():
        return json.loads(meta.read_text()), body.read_bytes()
    history = []
    content = b''
    status = 0
    for attempt in range(retries):
        try:
            r = (_session.get(url, params=params, timeout=timeout) if read_batch is None
                 else _session.post(url, json=read_batch, timeout=timeout))
            status, content = r.status_code, r.content
            history.append(status)
            if status != 429 and status < 500:
                break
            wait = max(float(r.headers.get('Retry-After', 0) or 0), min(60, 2 ** (attempt + 1)))
        except requests.RequestException as exc:
            history.append(type(exc).__name__)
            wait = min(60, 2 ** (attempt + 1))
        time.sleep(wait)
    info = dict(url=url, params=params, read_batch=read_batch, status=status, attempts=history,
                fetched_at=datetime.now(timezone.utc).isoformat(), bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest())
    tmp = body.with_suffix('.tmp')
    tmp.write_bytes(content)
    tmp.replace(body)
    meta.write_text(json.dumps(info, indent=2))
    time.sleep(0.5)
    return info, content


def audited_json(url, params=None, **kwargs):
    meta, content = cached_response(url, params, **kwargs)
    try:
        return meta, json.loads(content)
    except (ValueError, UnicodeDecodeError):
        return meta, None


def read_jsonl_gz(path):
    """Read a jsonl.gz that may still be being written (truncated tail tolerated)."""
    out = []
    try:
        with gzip.open(path, "rt") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    break
    except (EOFError, zlib.error):
        pass
    return out


def cached_get(url, params=None, cache_dir="http", max_age=None, sleep=0.1, retries=7):
    """GET JSON with an on-disk cache keyed by url+params."""
    key = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    d = DATA / cache_dir
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{key}.json.gz"
    if f.exists() and (max_age is None or time.time() - f.stat().st_mtime < max_age):
        with gzip.open(f, "rt") as fh:
            return json.load(fh)
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, timeout=60)
            if r.status_code == 200:
                j = r.json()
                with gzip.open(f, "wt") as fh:
                    json.dump(j, fh)
                time.sleep(sleep)
                return j
            if r.status_code in (400, 404):
                return None
            wait = min(60, 2 ** attempt)
        except (requests.RequestException, ValueError):
            wait = min(60, 2 ** attempt)
        time.sleep(wait)
    return None
