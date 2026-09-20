"""Keyless OpenAQ location index: brute-force location ids in the public S3 archive, keep those with 2020 data."""
import csv, gzip, io, sys
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore import UNSIGNED
from botocore.config import Config
s3 = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED, max_pool_connections=64))
B, ROOT = "openaq-data-archive", "records/csv.gz/"
def inspect(i):
    try:
        r = s3.list_objects_v2(Bucket=B, Prefix=f"{ROOT}locationid={i}/year=2020/month=02/", MaxKeys=1)
        c = r.get("Contents")
        if not c: return None
        rows = list(csv.DictReader(io.StringIO(gzip.decompress(s3.get_object(Bucket=B, Key=c[0]["Key"])["Body"].read()).decode("utf-8", "replace"))))
        return [i, rows[0]["location"], rows[0]["lat"], rows[0]["lon"], "|".join(sorted({x["parameter"] for x in rows}))]
    except Exception:
        return None
lo, hi = int(sys.argv[1]), int(sys.argv[2])
with ThreadPoolExecutor(64) as p, open(f"data/openaq_index_{lo}_{hi}.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "name", "lat", "lon", "params"])
    for r in p.map(inspect, range(lo, hi)):
        if r: w.writerow(r)
