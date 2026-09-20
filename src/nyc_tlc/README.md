# NYC TLC Trip Record Data — fetch guide

Monthly trip records from the NYC Taxi & Limousine Commission (yellow/green
taxis, for-hire vehicles, high-volume for-hire vehicles), published as Parquet.

- Registry: <https://registry.opendata.aws/nyc-tlc-trip-records-pds/>
- Official docs + data dictionaries: <https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>
- Bucket: `s3://nyc-tlc` (us-east-1)

## Access: credentials required for S3, CloudFront for everyone else

The `nyc-tlc` bucket does **not** allow anonymous S3 access — S3 requests must
be signed with AWS credentials. On your HackMIT EC2 instance the attached
IAM role (AmazonS3ReadOnlyAccess) provides these automatically, and the VPC's
S3 gateway endpoint makes same-region transfers free and fast.

If you have no AWS credentials (e.g. running on your laptop), use the
anonymous CloudFront mirror instead:

```
https://d37ci6vzurychx.cloudfront.net/trip-data/{filename}.parquet
https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```

`fetch.py --https` uses this automatically.

> Two gotchas:
> - The bucket denies `ListObjects` for everyone, so you cannot `aws s3 ls`
>   it — keys must be constructed by name (which `fetch.py` does).
> - Some AWS accounts are denied by the bucket policy even with valid
>   credentials (missing files and denied access both return 403). If signed
>   S3 fails for you, fall back to `--https`.

## Layout and file naming

| Location | S3 key | CloudFront path |
|---|---|---|
| Trip data | `trip data/{type}_tripdata_YYYY-MM.parquet` (prefix has a **space**) | `trip-data/{type}_tripdata_YYYY-MM.parquet` (hyphen) |
| Zone lookup | `misc/taxi_zone_lookup.csv` | `misc/taxi_zone_lookup.csv` |
| Zone shapefile | `misc/taxi_zones.zip` | `misc/taxi_zones.zip` |

`{type}` is one of `yellow`, `green`, `fhv`, `fhvhv`. Data availability:

| Type | First month | Notes |
|---|---|---|
| `yellow` | 2009-01 | Yellow medallion taxis (TPEP) |
| `green` | 2013-08 | Green boro taxis (LPEP) |
| `fhv` | 2015-01 | For-hire vehicles (livery/black car) |
| `fhvhv` | 2019-02 | High-volume FHV (Uber, Lyft, etc.) |

New months appear with roughly a 2–4 month publication delay (as of
September 2026 the latest month was 2026-05). A monthly yellow file is
~50–70 MB; fhvhv files are several hundred MB.

## Format and key columns

All trip files are **Parquet** (columnar; read with pandas + pyarrow, DuckDB,
polars, etc.). Full data dictionaries:

- [Yellow](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf)
- [Green](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_green.pdf)
- [FHV](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_fhv.pdf)
- [High-volume FHV](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_hvfhs.pdf)
- [Working with Parquet](https://www.nyc.gov/assets/tlc/downloads/pdf/working_parquet_format.pdf)

**Yellow / green** (yellow uses `tpep_*` datetime prefixes, green `lpep_*`):
`tpep_pickup_datetime` / `tpep_dropoff_datetime`, `PULocationID`,
`DOLocationID`, `passenger_count`, `trip_distance`, `RatecodeID`,
`payment_type`, `fare_amount`, `extra`, `mta_tax`, `tip_amount`,
`tolls_amount`, `improvement_surcharge`, `congestion_surcharge`,
`total_amount`. 2025+ files add `cbd_congestion_fee`.

**FHV**: `dispatching_base_num`, `pickup_datetime`, `dropOff_datetime`,
`PUlocationID`, `DOlocationID`, `SR_Flag`, `Affiliated_base_number`.

**FHVHV**: `hvfhs_license_num` (HV0003 = Uber, HV0005 = Lyft),
`dispatching_base_num`, `pickup_datetime`, `dropoff_datetime`,
`PULocationID`, `DOLocationID`, `trip_miles`, `trip_time`,
`base_passenger_fare`, `tolls`, `sales_tax`, `congestion_surcharge`, `tips`,
`driver_pay`, plus shared-ride and accessibility flags.

**Taxi zone lookup join**: pickup/dropoff locations are TLC zone IDs, not
coordinates. Join `PULocationID`/`DOLocationID` against
`taxi_zone_lookup.csv` (`LocationID`, `Borough`, `Zone`, `service_zone`) to
get names; use `misc/taxi_zones.zip` (shapefile) for geometry.

```python
import pandas as pd
trips = pd.read_parquet("data/nyc_tlc/yellow_tripdata_2026-05.parquet")
zones = pd.read_csv("data/nyc_tlc/taxi_zone_lookup.csv")
trips = trips.merge(zones.add_prefix("PU_"), left_on="PULocationID",
                    right_on="PU_LocationID", how="left")
```

## Using fetch.py

Slice args map directly to files: each (`--type`, year, month) combination
selects one `{type}_tripdata_YYYY-MM.parquet`. `--year`/`--month` accept a
single value or an inclusive `start:end` range. `--zones` adds
`taxi_zone_lookup.csv`.

```sh
# See what a slice contains (no download)
python3 fetch.py --list --type yellow --year 2024 --month 1:3

# Download Jan–Mar 2024 yellow + zone lookup
python3 fetch.py --type yellow --year 2024 --month 1:3 --zones

# Multiple types, one month
python3 fetch.py --type yellow --type green --year 2023 --month 6

# Default (no args): one recent month of yellow + zone lookup
python3 fetch.py

# No AWS credentials? Anonymous CloudFront download:
python3 fetch.py --https --type fhvhv --year 2024 --month 6
```

Other flags: `--output-dir DIR` (default `./data/nyc_tlc`),
`--max-size-gb N` (refuses downloads larger than N GB, default 5). Files
already present with matching size are skipped, so re-running is cheap.

## Setup on the EC2 instance (Amazon Linux 2023)

```sh
sudo dnf install -y python3-pip
pip3 install boto3                 # required for the default S3 mode
pip3 install pandas pyarrow        # optional, to read the Parquet files
```

`--https` mode needs no dependencies beyond the Python 3 stdlib.
