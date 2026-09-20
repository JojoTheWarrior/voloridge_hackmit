"""Download every 4th day of 2025 for sampled stations; keep daily-mean PM2.5 only."""
import boto3, csv, gzip, io, sys
import pandas as pd
from datetime import date, timedelta
from botocore import UNSIGNED
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor
SHARD, N = int(sys.argv[1]), int(sys.argv[2])
s3 = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED, max_pool_connections=32, retries={"max_attempts": 5}))
ids = pd.read_csv("stations_extra.csv", dtype={"id": str}).id.tolist()[SHARD::N]
days = [date(2025, 1, 1) + timedelta(days=k) for k in range(0, 365, 4)]
def get(job):
    i, d = job
    key = f"records/csv.gz/locationid={i}/year={d.year}/month={d.month:02d}/location-{i}-{d:%Y%m%d}.csv.gz"
    try:
        raw = s3.get_object(Bucket="openaq-data-archive", Key=key)["Body"].read()
    except Exception:
        return None
    v = [float(r["value"]) for r in csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8", "replace")))
         if r["parameter"] == "pm25" and r["value"]]
    ok = [x for x in v if 0 <= x < 1500]
    if not ok: return None
    return (i, d.isoformat(), sum(ok) / len(ok), len(ok), len(v))
with ThreadPoolExecutor(32) as ex, open(f"pm25_daily_x{SHARD}.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "date", "pm25", "n_ok", "n_raw"])
    for r in ex.map(get, [(i, d) for i in ids for d in days]):
        if r: w.writerow(r)
