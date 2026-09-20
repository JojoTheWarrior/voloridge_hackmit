# NOAA Integrated Surface Database (ISD) — fetch tool

Pulls slices of the [NOAA ISD](https://registry.opendata.aws/noaa-isd/) — global hourly
surface weather observations from **35,000+ stations**, some back to 1901 — from the
public S3 bucket. The full dataset is **~600 GB uncompressed and growing: always fetch a
slice**, never the whole thing.

## Bucket layout

- **Bucket:** `s3://noaa-isd-pds` (region `us-east-1`, public / anonymous access)
- **Data files:** `data/{year}/{USAF}-{WBAN}-{year}.gz`
  - One gzipped file per station per year. Years run `1901/` through the current year.
  - Example: `data/2024/725090-14739-2024.gz` (Boston Logan Intl, 2024, ~0.9 MB)
- **Station metadata at the bucket root:**
  - `isd-history.csv` — one row per station: `USAF, WBAN, STATION NAME, CTRY, STATE, ICAO, LAT, LON, ELEV(M), BEGIN, END`
  - `isd-inventory.csv` — per station **per year**: `USAF, WBAN, YEAR, JAN..DEC` (observation counts per month — use this to check a station actually has data for your year)
  - `isd-format-document.pdf` — the official record-format spec
  - `country-list.txt` — FIPS country-code lookup for the `CTRY` column
- Other prefixes (`isd-lite/`, `additional/`, `software/`, ...) exist but are not used by this tool.

Station IDs are `USAF-WBAN` pairs: USAF is a 6-digit Air Force catalog id, WBAN a
5-digit Weather Bureau id; `99999` fills in when one id doesn't exist.

## Record format (gzipped fixed-width ASCII)

Each line is one observation. Per the
[ISD format document](https://www.ncei.noaa.gov/data/global-hourly/doc/isd-format-document.pdf),
a record is a fixed **105-character mandatory section** followed by variable-length
`ADD` (additional), `REM` (remarks), and quality sections. Key mandatory-section
fields (1-based character positions):

| Positions | Field |
|---|---|
| 1–4    | total variable-section length |
| 5–10   | USAF station id |
| 11–15  | WBAN station id |
| 16–23  | observation date `YYYYMMDD` |
| 24–27  | observation time `HHMM` (UTC) |
| 29–34  | latitude (degrees ×1000, signed) |
| 35–41  | longitude (degrees ×1000, signed) |
| 47–51  | elevation (m, signed) |
| 61–63  | **wind direction** (degrees true, `999` = missing) + quality code |
| 66–69  | **wind speed** (m/s ×10, `9999` = missing) + quality code |
| 71–75  | ceiling height (m) |
| 79–84  | visibility (m) |
| 88–92  | **air temperature** (°C ×10, signed, `+9999` = missing) + quality code |
| 94–98  | **dew point** (°C ×10, signed) + quality code |
| 100–104| **sea-level pressure** (hPa ×10, `99999` = missing) + quality code |

Scaled values: divide by 10 (temp, dew point, pressure, wind speed) or 1000 (lat/lon).
All-9s means missing. The `ADD` section carries precipitation, snow depth, weather
codes, etc. — see the format doc. If you'd rather skip fixed-width parsing, the sibling
bucket `s3://noaa-global-hourly-pds` has the same data as CSV.

## Finding stations

1. Grab metadata: `python src/noaa_isd/fetch.py` (default run) downloads
   `isd-history.csv` + `isd-inventory.csv`.
2. Search `isd-history.csv` by `STATION NAME`, `CTRY` (FIPS code), `STATE`, `ICAO`, or
   lat/lon; the station id is `USAF-WBAN` from the first two columns. Check
   `BEGIN`/`END` for the period of record.
3. Cross-check `isd-inventory.csv` to confirm the station reports data in the years you
   want (monthly observation counts).

## How slice args map to S3 keys

| Arg | Keys selected |
|---|---|
| `--year 2023` | `data/2023/*` |
| `--year 2020:2023` | `data/2020/*` … `data/2023/*` (inclusive range) |
| `--station 725090-14739` | `data/{year}/725090-14739-{year}.gz` (repeatable) |
| `--stations-file f.txt` | one `USAF-WBAN` per line, `#` comments OK |
| `--country US` | all stations whose `CTRY` matches in `isd-history.csv` |
| `--metadata` | also fetch `isd-history.csv` + `isd-inventory.csv` |
| *(no slice args)* | metadata + `data/2024/725090-14739-2024.gz` (small, safe default) |

Other flags: `--list` (show keys + total size, no download), `--max-size-gb N`
(refuse download above N GB, default 5), `--output-dir DIR` (default
`./data/noaa_isd`; keys mirror bucket paths), `--signed` (use AWS credentials
instead of anonymous). Already-downloaded files with matching sizes are skipped,
so re-runs resume.

## Examples

```bash
# Safe default: station metadata + Boston Logan 2024 (~19 MB)
python src/noaa_isd/fetch.py

# Preview a slice without downloading
python src/noaa_isd/fetch.py --list --year 2020:2024 --station 725090-14739

# Two stations, five years
python src/noaa_isd/fetch.py --year 2020:2024 --station 725090-14739 --station 722950-23174

# Every Japanese station for 2023 (list first to check size!)
python src/noaa_isd/fetch.py --list --year 2023 --country JA
python src/noaa_isd/fetch.py --year 2023 --country JA --max-size-gb 2

# Stations from a file, with metadata
python src/noaa_isd/fetch.py --year 2024 --stations-file my_stations.txt --metadata
```

## Running on the HackMIT EC2 instances

Instances are Amazon Linux 2023 in `us-east-1` — same region as the bucket, so
transfers are free and fast via the S3 gateway endpoint. You may need to install
boto3 first:

```bash
sudo dnf install -y python3-pip && pip3 install boto3
```

Anonymous access (the default) works out of the box; `--signed` also works since the
instances carry the `AmazonS3ReadOnlyAccess` role.

## Official documentation

- Registry entry: <https://registry.opendata.aws/noaa-isd/>
- Format spec: <https://www.ncei.noaa.gov/data/global-hourly/doc/isd-format-document.pdf>
- NCEI ISD homepage: <https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database>
