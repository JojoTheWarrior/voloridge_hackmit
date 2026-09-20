"""Shared paths and polite, cached HTTP helpers for the dams-from-space pipeline."""
import hashlib
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
for _d in (DATA, CACHE, RESULTS, FIGURES):
    _d.mkdir(exist_ok=True)

GWW = "https://api.globalwaterwatch.earth"
UA = {"User-Agent": "hackmit-dams-research/0.1 (academic hackathon; cached, low-rate)"}
SESSION = requests.Session()
SESSION.headers.update(UA)


def cached_json(url, params=None, body=None, subdir="http", key=None, sleep=0.0, retries=5, timeout=180,
                ok=lambda j: True):
    """GET (or POST when body is given) JSON with an on-disk cache and exponential backoff."""
    d = CACHE / subdir
    d.mkdir(parents=True, exist_ok=True)
    if key is None:
        key = hashlib.sha1(json.dumps([url, params, body], sort_keys=True).encode()).hexdigest()
    fn = d / f"{key}.json"
    if fn.exists():
        return json.loads(fn.read_text())
    err = None
    for i in range(retries):
        try:
            r = SESSION.post(url, json=body, timeout=timeout) if body is not None else SESSION.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                j = r.json()
                if ok(j):
                    fn.write_text(json.dumps(j))
                    if sleep:
                        time.sleep(sleep)
                    return j
                err = f"not ok: {str(j)[:200]}"
            else:
                err = f"{r.status_code} {r.text[:200]}"
        except Exception as e:  # network errors are retried
            err = repr(e)
        time.sleep(min(90, 3 * 2 ** i))
    raise RuntimeError(f"failed {url} {params}: {err}")
