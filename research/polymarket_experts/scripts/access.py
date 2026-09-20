"""Serial, cached, public read-only HTTP with bounded backoff. No auth support."""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/access"
CACHE.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "public-research-audit/1.0"


def get(name, url, params=None, post=None):
    body = CACHE / (name + ".body")
    meta = CACHE / (name + ".json")
    if meta.exists() and body.exists():
        m = json.loads(meta.read_text())
        return m, body.read_bytes()
    # POST is allowed only for explicit read-only RPC/GraphQL, never mutation.
    if post is not None:
        method = post.get("method")
        query = post.get("query", "")
        if method not in [
            "eth_blockNumber",
            "eth_getLogs",
            "eth_getTransactionReceipt",
            "eth_getBlockByNumber",
        ] and not (
            query.lstrip().startswith("{") or query.lstrip().startswith("query")
        ):
            raise ValueError("Only read-only RPC and GraphQL queries permitted")
    for attempt in range(4):
        time.sleep(0.5)
        try:
            r = (
                SESSION.get(url, params=params, timeout=(10, 40))
                if post is None
                else SESSION.post(url, json=post, timeout=(10, 40))
            )
            if (r.status_code == 429 or r.status_code >= 500) and attempt < 3:
                time.sleep(2**attempt)
                continue
            b = r.content
            m = {
                "name": name,
                "url": url,
                "params": params,
                "query": post,
                "status": r.status_code,
                "bytes": len(b),
                "sha256": hashlib.sha256(b).hexdigest(),
                "accessed_at": datetime.now(timezone.utc).isoformat(),
                "headers": {
                    k: v
                    for k, v in r.headers.items()
                    if k.lower()
                    in [
                        "content-type",
                        "content-length",
                        "last-modified",
                        "etag",
                        "retry-after",
                    ]
                },
            }
            break
        except requests.RequestException as e:
            if attempt < 3:
                time.sleep(2**attempt)
                continue
            b = b""
            m = {
                "name": name,
                "url": url,
                "params": params,
                "query": post,
                "status": 0,
                "error": type(e).__name__,
                "accessed_at": datetime.now(timezone.utc).isoformat(),
            }
    body.write_bytes(b)
    meta.write_text(json.dumps(m, indent=2))
    return m, b


def show(name, url, params=None, post=None):
    m, b = get(name, url, params, post)
    print(name, m["status"], len(b), flush=True)
    return b


if __name__ == "__main__":
    import sys

    show(sys.argv[1], sys.argv[2])
