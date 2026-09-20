"""Enumerate provider=/country=/locationid= partitions of the OpenAQ archive (anonymous)."""
import boto3, csv
from botocore import UNSIGNED
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor
s3 = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED, max_pool_connections=64))
ROOT = "records/csv.gz/"
def prefixes(p):
    out = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket="openaq-data-archive", Prefix=p, Delimiter="/"):
        out += [c["Prefix"] for c in page.get("CommonPrefixes", [])]
    return out
provs = [p for p in prefixes(ROOT) if "provider=" in p]
pcs = [pc for p in provs for pc in prefixes(p)]
def locs(pc):
    rows = []
    for l in prefixes(pc):
        years = [y.rstrip("/").split("=")[-1] for y in prefixes(l)]
        parts = dict(x.split("=") for x in l.rstrip("/").split("/")[2:])
        rows.append({**parts, "years": "|".join(years)})
    return rows
with ThreadPoolExecutor(32) as ex:
    rows = [r for rs in ex.map(locs, pcs) for r in rs]
with open("provider_locations.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["provider", "country", "locationid", "years"]); w.writeheader(); w.writerows(rows)
print(len(provs), len(pcs), len(rows))
