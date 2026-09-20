"""Build a keyless OpenAQ location index from the S3 archive: lat/lon, params, days with data in 2024/2025."""
import boto3, csv, gzip, io, sys
from botocore import UNSIGNED
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor
s3 = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED, max_pool_connections=96, retries={"max_attempts": 5}))
B, ROOT = "openaq-data-archive", "records/csv.gz/"
SHARD, NSHARD = int(sys.argv[1]), int(sys.argv[2])
ids = [l.split("locationid=")[1].strip("/\n") for l in open("ids_raw.txt") if "locationid=" in l][SHARD::NSHARD]
def keys(i, y):
    r = s3.list_objects_v2(Bucket=B, Prefix=f"{ROOT}locationid={i}/year={y}/")
    return [c["Key"] for c in r.get("Contents", [])]
def inspect(i):
    try:
        k25, k24 = keys(i, 2025), keys(i, 2024)
        ks = k25 or k24
        if not ks:
            return {"id": i, "n2024": 0, "n2025": 0}
        raw = s3.get_object(Bucket=B, Key=ks[len(ks)//2])["Body"].read()
        rows = list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8", "replace"))))
        pm = [float(r["value"]) for r in rows if r["parameter"] == "pm25" and r["value"] not in ("", None)]
        return {"id": i, "n2024": len(k24), "n2025": len(k25), "name": rows[0]["location"], "lat": rows[0]["lat"], "lon": rows[0]["lon"],
                "params": "|".join(sorted({r["parameter"] for r in rows})), "n_pm25_rows_sample_day": len(pm),
                "sample_key": ks[len(ks)//2]}
    except Exception as e:
        return {"id": i, "error": str(e)[:100]}
fields = ["id", "n2024", "n2025", "name", "lat", "lon", "params", "n_pm25_rows_sample_day", "sample_key", "error"]
with open(f"location_index_{SHARD}.csv", "w", newline="") as f, ThreadPoolExecutor(24) as ex:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
    for n, row in enumerate(ex.map(inspect, ids)):
        w.writerow(row)
        if n % 2000 == 0: print(n, file=sys.stderr, flush=True); f.flush()
