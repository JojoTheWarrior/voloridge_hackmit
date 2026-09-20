# OpenAQ Air Quality Data — Fetch Guide

Global air quality measurements from [OpenAQ](https://openaq.org/), hosted in the
[AWS Open Data Registry](https://registry.opendata.aws/openaq/).

- **Bucket:** `s3://openaq-data-archive` (region `us-east-1` — same region as your EC2 instance, so transfers are free and fast via the S3 gateway endpoint)
- **Access:** public / anonymous (`--no-sign-request` works; no credentials needed)
- **Official docs:** [docs.openaq.org/aws/about](https://docs.openaq.org/aws/about) · [Quick start](https://docs.openaq.org/aws/quick-start) · [OpenAQ API docs](https://docs.openaq.org)

## Bucket layout (verified 2026-09)

Hive-style partitioning under a fixed `records/csv.gz/` root:

```
records/
└── csv.gz/
    └── locationid={locationid}/          e.g. locationid=2178
        └── year={YYYY}/                  e.g. year=2024
            └── month={MM}/               zero-padded, e.g. month=01
                └── location-{locationid}-{YYYYMMDD}.csv.gz
```

Example real key:

```
records/csv.gz/locationid=2178/year=2024/month=01/location-2178-20240101.csv.gz
```

Each object is a **gzipped CSV holding all measurements for one location for one day**
(all of its sensors/parameters). Files are typically small — 1 KB to a few hundred KB —
and are written ~72 hours after the end of the location's local day. There is no
locations metadata file in the bucket itself; use the OpenAQ API for discovery (below).

## CSV schema (verified against a real file)

Header row is quoted; one measurement per row (narrow format):

| column        | description                                            | example                     |
|---------------|--------------------------------------------------------|-----------------------------|
| `location_id` | OpenAQ location id of the station                      | `2178`                      |
| `sensors_id`  | OpenAQ sensor id of the pollutant measured             | `3916`                      |
| `location`    | station name                                           | `Del Norte-2178`            |
| `datetime`    | ISO-8601 timestamp with timezone offset                | `2024-01-01T05:00:00-07:00` |
| `lat`         | latitude, decimal degrees (EPSG:4326)                  | `35.1353`                   |
| `lon`         | longitude, decimal degrees (EPSG:4326)                 | `-106.584702`               |
| `parameter`   | pollutant, e.g. `pm25`, `pm10`, `no2`, `o3`, `so2`, `co` | `no2`                     |
| `units`       | measurement unit                                       | `ppm`, `µg/m³`              |
| `value`       | measured value (decimal)                               | `0.0301`                    |

## Discovering location IDs

The bucket has no index of locations, so use either:

1. **OpenAQ API** (needs a free [API key](https://docs.openaq.org/using-the-api/api-key)):
   ```bash
   curl -H "X-API-Key: YOUR_KEY" "https://api.openaq.org/v3/locations?coordinates=42.36,-71.09&radius=25000&limit=100"
   ```
   Each result's `id` is the `locationid` used in the bucket. You can filter by
   country, coordinates+radius, parameter, provider, etc. See
   [locations docs](https://docs.openaq.org/resources/locations).
2. **List the bucket** to check whether a given id has data and for which years:
   ```bash
   aws s3 ls --no-sign-request s3://openaq-data-archive/records/csv.gz/locationid=2178/
   ```

## fetch.py

Stdlib + `boto3` only. Anonymous (unsigned) S3 access by default; `--signed` uses the
default credential chain (e.g. the instance IAM role).

### On a fresh Amazon Linux 2023 EC2 instance

```bash
sudo dnf install -y python3-pip && pip3 install boto3
```

### Slice arguments → S3 prefixes

| argument          | maps to                                    | notes                                        |
|-------------------|--------------------------------------------|----------------------------------------------|
| `--location-id N` | `records/csv.gz/locationid=N/`             | repeatable for multiple locations            |
| `--year Y`        | `.../year=Y/`                              | range ok: `2023:2024`, lists ok: `2022,2024` |
| `--month M`       | `.../month=MM/` (zero-padded)              | range ok: `1:6`                              |

The script builds the narrowest prefix it can from your args and lists only that.
With **no arguments** it downloads one small default slice (location `2178`, most
recent full month) — it never fetches the whole archive. `--max-size-gb` (default 5)
aborts before downloading any slice larger than the cap.

Other flags: `--output-dir` (default `./data/openaq`), `--list` (show matching keys +
total size, no download), `--signed`. Already-downloaded files with matching sizes are
skipped, so re-running resumes an interrupted fetch. Files land under the output dir
mirroring the bucket layout, so tools like DuckDB/Athena/pandas can use the
hive partitions.

### Examples

```bash
# See what a slice contains without downloading anything
python3 fetch.py --list --location-id 2178 --year 2024 --month 1

# One location, first half of 2023
python3 fetch.py --location-id 2178 --year 2023 --month 1:6

# Two locations, two full years, custom destination
python3 fetch.py --location-id 2178 --location-id 8118 --year 2023:2024 --output-dir /data/aq

# Everything for one location (all years) — check size first with --list!
python3 fetch.py --list --location-id 2178
python3 fetch.py --location-id 2178 --max-size-gb 2

# Default tiny slice (location 2178, last full month)
python3 fetch.py
```

### Reading the data

```python
import glob, gzip, pandas as pd
frames = [pd.read_csv(f) for f in glob.glob("data/openaq/records/csv.gz/**/*.csv.gz", recursive=True)]
df = pd.concat(frames, ignore_index=True)
```
