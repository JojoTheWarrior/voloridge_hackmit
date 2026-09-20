# PUDL — Public Utility Data Liberation Project

Analysis-ready US energy system data (EIA, EPA, FERC, PHMSA, SEC) from
[Catalyst Cooperative](https://catalyst.coop/), served from a public S3 bucket.

- **Bucket:** `s3://pudl.catalyst.coop` (region `us-west-2`, anonymous access OK)
- **Registry:** https://registry.opendata.aws/catalyst-cooperative-pudl/

> **Note on region/cost:** this bucket lives in `us-west-2`, so downloads from
> the `us-east-1` instances bypass the S3 gateway endpoint and route over the
> internet gateway. This is still free: data transfer *into* EC2 is $0.00/GB,
> the instances use public IPs (no NAT gateway), and the bucket is not
> Requester Pays — egress is covered by the AWS Open Data program.
- **Data access docs:** https://catalystcoop-pudl.readthedocs.io/en/latest/data_access.html
- **Data dictionary (table definitions):** https://catalystcoop-pudl.readthedocs.io/en/latest/data_dictionaries/pudl_db.html
- **License:** CC-BY-4.0

## Bucket layout

Top-level prefixes are *releases*:

| Prefix | Meaning |
|---|---|
| `stable/` | Latest versioned release — **recommended default** |
| `nightly/` | Nightly CI build outputs (fresher, less vetted) |
| `vYYYY.M.N/` | Pinned versioned releases (e.g. `v2026.8.0`, `v2025.2.0`) for reproducibility |
| `ferceqr/`, `zenodo/`, `staging/`, ... | Other/internal resources — not needed here |

Inside a release, each database table is a single Apache Parquet file directly
under the prefix, named `<table_name>.parquet`:

```
s3://pudl.catalyst.coop/stable/core_eia__entity_plants.parquet
s3://pudl.catalyst.coop/stable/out_ferc1__yearly_all_plants.parquet
```

A release also contains bulk archives (`pudl.sqlite.zip` ~3.4 GB,
`pudl_parquet.zip` ~12 GB), raw FERC databases (`ferc1_dbf/`,
`ferc1_xbrl.sqlite.zip`, ...), and Census GIS data — the fetch script ignores
these and only handles the per-table parquet files (~440 tables in `stable`).

## Table families

- **`core_eia*`** — cleaned EIA data: `core_eia860__*` (generators, plants,
  utilities, ownership), `core_eia923__*` (generation, fuel), `core_eia861__*`
  (sales, demand response), `core_eia__entity_*` (small static entity tables),
  `core_eia__codes_*` (tiny code/label tables).
- **`core_ferc1*`** — FERC Form 1 utility financials (balance sheets, income
  statements, plant-in-service, steam plants...).
- **`out_*`** — denormalized, analysis-ready outputs joining multiple core
  tables (e.g. `out_eia__yearly_generators`, `out_ferc1__yearly_all_plants`,
  `out_eia923__monthly_generation_fuel_combined`). Usually the best starting
  point for analysis.
- **`core_epacems__hourly_emissions`** — ⚠️ EPA CEMS hourly power plant
  emissions. This single parquet file is **~4.9 GB**. Don't fetch it casually;
  the default 5 GB safety cap will (barely) allow it, so think before you do.
  `out_vcerare__hourly_available_capacity_factor` is similarly huge (~3.6 GB).
- Also: `core_phmsagas__*` (gas pipelines), `out_sec10k__*` (SEC filings),
  `out_ferc714__*` (hourly demand), `core_pudl__*` (ID crosswalks).

To understand a table's columns and meaning, look it up by name in the
[PUDL data dictionary](https://catalystcoop-pudl.readthedocs.io/en/latest/data_dictionaries/pudl_db.html).

## fetch.py

Slice args map to S3 keys as `s3://pudl.catalyst.coop/<release>/<table>.parquet`:

- `--release` → the release prefix (`stable` default, `nightly`, or `vYYYY.M.N`)
- `--table NAME` → exact table name, or case-insensitive substring matching
  multiple tables; repeatable
- `--list-tables` → enumerate all tables (with sizes) in the release
- `--list` → show matched keys + total size without downloading
- `--max-size-gb` → refuse downloads above this cap (default 5)
- `--output-dir` → where files land (default `./data/pudl`)
- `--signed` → use AWS credentials instead of anonymous access
- no args → downloads a small (~2 MB) sample: `core_eia__entity_plants`,
  `core_eia__entity_utilities`, `core_eia__entity_generators`

### Examples

```bash
# Small default sample (plants/utilities/generators entity tables)
python3 fetch.py

# What tables exist in the stable release?
python3 fetch.py --list-tables

# Preview all FERC Form 1 denormalized outputs without downloading
python3 fetch.py --table out_ferc1 --list

# Fetch specific tables
python3 fetch.py --table core_eia860__scd_plants --table core_eia860__scd_utilities

# Pin an exact release for reproducibility
python3 fetch.py --release v2026.8.0 --table out_eia__yearly_generators

# On an EC2 instance with an IAM role, signed requests also work
python3 fetch.py --signed --table core_eia__entity_plants
```

## Setup on the HackMIT EC2 instances (Amazon Linux 2023)

```bash
sudo dnf install -y python3-pip
pip3 install boto3
# to actually read the parquet files:
pip3 install pandas pyarrow
```

Then, e.g.:

```python
import pandas as pd
df = pd.read_parquet("data/pudl/core_eia__entity_plants.parquet")
```

Note: the bucket lives in `us-west-2`; the instances' S3 gateway endpoint is in
`us-east-1`, so transfers are cross-region but still free to you (the bucket is
Requester-Pays-free public open data).
