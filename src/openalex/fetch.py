#!/usr/bin/env python3
"""Fetch slices of the OpenAlex snapshot from s3://openalex.

The snapshot lives at s3://openalex/data/jsonl/{entity}/updated_date=YYYY-MM-DD/part_NNNN.gz
(gzipped JSON Lines, one entity object per line). Each entity prefix also holds a
manifest.json listing every part file with its size and record count, which this
script uses to plan downloads without paginating the bucket.

Anonymous (unsigned) access is used by default; pass --signed to use your
configured AWS credentials/IAM role instead (e.g. on the HackMIT EC2 instances).

Requires: Python 3.10+, boto3 (pip install boto3).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKET = "openalex"
REGION = "us-east-1"
JSONL_PREFIX = "data/jsonl"

# Entities present under s3://openalex/data/jsonl/ (verified 2026-09).
ENTITIES = [
    "authors",
    "awards",
    "concepts",
    "continents",
    "countries",
    "domains",
    "fields",
    "funders",
    "institution-types",
    "institutions",
    "keywords",
    "languages",
    "licenses",
    "publishers",
    "sdgs",
    "source-types",
    "sources",
    "subfields",
    "topics",
    "work-types",
    "works",
]

# Small entity used for the no-args default download.
DEFAULT_ENTITY = "concepts"


@dataclass
class PartFile:
    key: str  # S3 key, e.g. data/jsonl/concepts/updated_date=2026-06-26/part_0000.gz
    size: int
    updated_date: str  # YYYY-MM-DD
    record_count: int | None = None


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def make_client(signed: bool):
    if signed:
        return boto3.client("s3", region_name=REGION)
    return boto3.client(
        "s3", region_name=REGION, config=Config(signature_version=UNSIGNED)
    )


def load_manifest(s3, entity: str) -> dict:
    key = f"{JSONL_PREFIX}/{entity}/manifest.json"
    body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    return json.loads(body)


def parse_updated_date(key: str) -> str:
    # .../updated_date=YYYY-MM-DD/part_NNNN.gz
    for seg in key.split("/"):
        if seg.startswith("updated_date="):
            return seg.removeprefix("updated_date=")
    return ""


def select_parts(
    manifest: dict,
    updated_since: str | None,
    updated_date: str | None,
    max_files: int | None,
) -> list[PartFile]:
    parts: list[PartFile] = []
    for f in manifest.get("files", []):
        key = f["url"].removeprefix(f"s3://{BUCKET}/")
        date = parse_updated_date(key)
        if updated_date and date != updated_date:
            continue
        if updated_since and date < updated_since:
            continue
        meta = f.get("meta", {})
        parts.append(
            PartFile(
                key=key,
                size=meta.get("content_length", 0),
                updated_date=date,
                record_count=meta.get("record_count"),
            )
        )
    # Most recent partitions first, so --max-files keeps the freshest data.
    parts.sort(key=lambda p: (p.updated_date, p.key), reverse=True)
    if max_files is not None:
        parts = parts[:max_files]
    return parts


def download_file(s3, key: str, dest: Path, size: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    done = 0

    def cb(n: int) -> None:
        nonlocal done
        done += n
        if size:
            pct = 100 * done / size
            print(f"\r    {human_size(done)} / {human_size(size)} ({pct:.0f}%)",
                  end="", flush=True)

    tmp = dest.with_suffix(dest.suffix + ".part")
    s3.download_file(BUCKET, key, str(tmp), Callback=cb)
    tmp.replace(dest)
    print()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Download slices of the OpenAlex snapshot (s3://openalex).",
        epilog="With no arguments, downloads the manifest plus the single most "
               f"recent part file of the small '{DEFAULT_ENTITY}' entity.",
    )
    p.add_argument("--output-dir", default="./data/openalex",
                   help="destination directory (default: ./data/openalex)")
    p.add_argument("--entity", action="append", choices=ENTITIES + ["all"],
                   metavar="ENTITY",
                   help=f"entity to fetch; repeatable, or 'all'. Choices: "
                        f"{', '.join(ENTITIES)}, all")
    p.add_argument("--updated-since", metavar="YYYY-MM-DD",
                   help="only partitions with updated_date >= this date")
    p.add_argument("--updated-date", metavar="YYYY-MM-DD",
                   help="only the exact updated_date= partition")
    p.add_argument("--max-files", type=int, metavar="N",
                   help="cap on part files per entity (most recent first)")
    p.add_argument("--list", action="store_true",
                   help="list matching keys and total size; do not download")
    p.add_argument("--max-size-gb", type=float, default=5.0, metavar="GB",
                   help="refuse to download slices larger than this (default: 5)")
    p.add_argument("--signed", action="store_true",
                   help="use AWS credentials instead of anonymous access")
    args = p.parse_args(argv)

    default_mode = False
    entities = args.entity or []
    if "all" in entities:
        entities = list(ENTITIES)
    if not entities:
        # Safe default: one small entity, one most-recent file.
        default_mode = True
        entities = [DEFAULT_ENTITY]
        if args.max_files is None:
            args.max_files = 1

    s3 = make_client(args.signed)
    out_root = Path(args.output_dir)

    plan: list[tuple[str, list[PartFile]]] = []
    total_size = 0
    for entity in entities:
        try:
            manifest = load_manifest(s3, entity)
        except Exception as e:  # noqa: BLE001
            print(f"error: could not read manifest for '{entity}': {e}",
                  file=sys.stderr)
            return 1
        parts = select_parts(manifest, args.updated_since, args.updated_date,
                             args.max_files)
        plan.append((entity, parts))
        total_size += sum(pt.size for pt in parts)

    if args.list:
        for entity, parts in plan:
            print(f"{entity}: {len(parts)} file(s), "
                  f"{human_size(sum(pt.size for pt in parts))}")
            for pt in parts:
                recs = f", {pt.record_count} records" if pt.record_count else ""
                print(f"  s3://{BUCKET}/{pt.key}  ({human_size(pt.size)}{recs})")
        print(f"\nTOTAL: {sum(len(x[1]) for x in plan)} file(s), "
              f"{human_size(total_size)}")
        return 0

    cap = args.max_size_gb * 1024**3
    if total_size > cap:
        print(f"error: slice is {human_size(total_size)}, which exceeds the "
              f"--max-size-gb cap of {args.max_size_gb} GB.\n"
              f"Narrow it with --updated-since/--updated-date/--max-files, or "
              f"raise --max-size-gb if you really mean it.", file=sys.stderr)
        return 1

    if default_mode:
        print(f"No slice arguments given; downloading the {DEFAULT_ENTITY} "
              f"manifest + its most recent part file. Use --entity/--list to "
              f"choose a slice.")

    n_total = sum(len(x[1]) for x in plan)
    print(f"Downloading {n_total} file(s), {human_size(total_size)} "
          f"-> {out_root}")
    i = 0
    for entity, parts in plan:
        # Always save the entity manifest alongside the data.
        mdest = out_root / entity / "manifest.json"
        mdest.parent.mkdir(parents=True, exist_ok=True)
        mkey = f"{JSONL_PREFIX}/{entity}/manifest.json"
        s3.download_file(BUCKET, mkey, str(mdest))
        print(f"  saved {mdest}")
        for pt in parts:
            i += 1
            rel = pt.key.removeprefix(f"{JSONL_PREFIX}/")
            dest = out_root / rel
            if dest.exists() and dest.stat().st_size == pt.size:
                print(f"  [{i}/{n_total}] skip (exists) {rel}")
                continue
            print(f"  [{i}/{n_total}] {rel} ({human_size(pt.size)})")
            download_file(s3, pt.key, dest, pt.size)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
