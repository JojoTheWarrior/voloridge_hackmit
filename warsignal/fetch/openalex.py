from __future__ import annotations

import argparse
import json
import os
import csv
import time
from datetime import date, timedelta
from pathlib import Path

import boto3
import pandas as pd
import requests
from botocore import UNSIGNED
from botocore.config import Config

from warsignal.config import OPENALEX_QUERIES, env
from warsignal.fetch.common import manifest, output_dir, parse_date

def _group_counts(query: str, start: date, end: date):
    base = "https://api.openalex.org/works"
    params = {"filter": f"title_and_abstract.search:{query},from_publication_date:{start},to_publication_date:{end}", "group_by": "publication_date", "per-page": 200, "mailto": "hackmit@example.com"}
    if env("OPENALEX_API_KEY"):
        params["api_key"] = env("OPENALEX_API_KEY")
    response = requests.get(base, params=params, timeout=60)
    data = response.json()
    if not response.ok or isinstance(data, dict) and data.get("error"):
        raise RuntimeError(data.get("message") or data.get("error") or f"HTTP {response.status_code}")
    groups = data.get("group_by")
    if not isinstance(groups, list):
        raise RuntimeError("OpenAlex response did not contain group_by")
    return [(item["key"], item["count"]) for item in groups], "publication_date"

def fetch_works_sample(n_files: int = 12, max_file_mb: int = 400, start: date = date(2025, 1, 1),
                       end: date = date.today(), keep_raw: bool = False) -> Path:
    client = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))
    partitions = {}
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket="openalex", Prefix="data/parquet/works/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if "updated_date=" not in key or obj["Size"] >= max_file_mb * 1024**2:
                continue
            partition = key.split("updated_date=", 1)[1][:10]
            if partition >= "2025-07-01":
                partitions.setdefault(partition, []).append(obj)
    ordered = sorted(partitions, key=lambda p: (not p.startswith("2026"), p))
    candidates = []
    for partition in ordered:
        candidates.append(min(partitions[partition], key=lambda item: item["Size"]))
        if len(candidates) >= n_files:
            break
    if not candidates:
        raise RuntimeError("no OpenAlex parquet shards matched the requested partitions")
    raw_dir = output_dir("openalex") / "sample_raw"
    raw_paths = []
    for obj in candidates:
        path = raw_dir / Path(obj["Key"]).name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size == 0:
            client.download_file("openalex", obj["Key"], str(path))
            manifest("openalex", f"s3://openalex/{obj['Key']}", obj["Size"], start, end,
                     key=obj["Key"], status="downloaded", sample=True)
        raw_paths.append(path)
    import pandas as pd
    rows = []
    for path in raw_paths:
        frame = pd.read_parquet(path, columns=["id", "publication_date", "title", "primary_topic",
                                                "keywords", "abstract_inverted_index", "authorships",
                                                "cited_by_count"])
        for row in frame.to_dict("records"):
            published = row.get("publication_date")
            if not published or not (start.isoformat() <= str(published) <= end.isoformat()):
                continue
            topic = row.get("primary_topic") or {}
            if not isinstance(topic, dict):
                topic = {}
            authorships = row.get("authorships")
            if authorships is None:
                authorships = []
            elif hasattr(authorships, "tolist"):
                authorships = authorships.tolist()
            iran = any(
                institution.get("country_code") == "IR"
                for author in authorships if isinstance(author, dict)
                for institution in (author.get("institutions") if author.get("institutions") is not None else []) if isinstance(institution, dict)
            )
            keywords = row.get("keywords")
            if keywords is None:
                keywords = []
            elif hasattr(keywords, "tolist"):
                keywords = keywords.tolist()
            keyword_text = "|".join(str(k.get("display_name", "")) for k in keywords if isinstance(k, dict))
            abstract = row.get("abstract_inverted_index")
            if isinstance(abstract, str):
                try:
                    abstract = json.loads(abstract)
                except json.JSONDecodeError:
                    abstract = {}
            abstract_words = " ".join(str(k).lower() for k in (abstract or {}).keys())[:2000]
            rows.append({
                "id": row.get("id"), "publication_date": str(published), "title": row.get("title"),
                "primary_topic_name": topic.get("display_name"), "primary_field": (topic.get("field") or {}).get("display_name"),
                "keywords": keyword_text, "abstract_words": abstract_words, "has_abstract": bool(abstract),
                "cited_by_count": row.get("cited_by_count"), "iran_affiliated": iran,
            })
    result = pd.DataFrame(rows)
    destination = output_dir("openalex") / "works_sample.parquet"
    result.to_parquet(destination, index=False)
    manifest("openalex", "s3://openalex/data/parquet/works/", destination.stat().st_size, start, end,
             status="built", files=len(raw_paths), rows=len(result))
    if not keep_raw:
        for path in raw_paths:
            path.unlink(missing_ok=True)
        raw_dir.rmdir()
    return destination

def fetch(start=date(2025, 3, 1), end=date.today(), quick=False, **_) -> list[Path]:
    items = list(OPENALEX_QUERIES.items())[:5] if quick else list(OPENALEX_QUERIES.items())
    paths = []
    for key, query in items:
        try:
            groups, grouping = _group_counts(query, start, end)
            path = output_dir("openalex") / f"counts_{key}.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle); writer.writerow(["date", "count"]); writer.writerows(groups)
            manifest("openalex", "https://api.openalex.org/works", path.stat().st_size, start, end, query=query, grouping=grouping, status="downloaded")
            paths.append(path)
        except Exception as exc:
            manifest("openalex", "https://api.openalex.org/works", 0, start, end,
                     query=query, status="error", error=str(exc))
            print(f"openalex: {key} failed: {exc}")
        time.sleep(0.2)
    if not quick:
        paths.append(fetch_works_sample(start=start, end=end))
    print(f"openalex: {len(paths)} files")
    return paths

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--quick", action="store_true")
    p.add_argument("--sample", action="store_true"); p.add_argument("--keep-raw", action="store_true"); p.add_argument("--sample-files", type=int, default=12); a = p.parse_args()
    from warsignal.config import START, END
    start = parse_date(a.start) if a.start else START; end = parse_date(a.end) if a.end else END
    if a.sample:
        print(fetch_works_sample(n_files=a.sample_files, start=start, end=end, keep_raw=a.keep_raw))
    else:
        fetch(start, end, quick=a.quick)
