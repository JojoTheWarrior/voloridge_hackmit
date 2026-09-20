"""Keyless OpenAQ archive reader: daily means per location/parameter."""
import csv, gzip, io
from concurrent.futures import ThreadPoolExecutor
import boto3, pandas as pd
from botocore import UNSIGNED
from botocore.config import Config
s3 = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED, max_pool_connections=64))
B = "openaq-data-archive"
def _keys(loc, year, months):
    out = []
    for m in months:
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=B, Prefix=f"records/csv.gz/locationid={loc}/year={year}/month={m:02d}/"):
            out += [o["Key"] for o in page.get("Contents", [])]
    return out
def _read(k):
    try: return pd.read_csv(io.BytesIO(s3.get_object(Bucket=B, Key=k)["Body"].read()), compression="gzip", usecols=["datetime", "parameter", "value"])
    except Exception: return None
def hourly(loc, year, months, param):
    with ThreadPoolExecutor(48) as p: fr = [f for f in p.map(_read, _keys(loc, year, months)) if f is not None]
    if not fr: return pd.Series(dtype=float)
    d = pd.concat(fr); d = d[(d.parameter == param) & (d.value > -1) & (d.value < 2000)]
    d["t"] = pd.to_datetime(d.datetime, utc=True).dt.tz_convert(None)
    return d.groupby("t").value.mean().sort_index()
def daily(loc, year, months, param): 
    h = hourly(loc, year, months, param); return h.resample("D").mean() if len(h) else h
