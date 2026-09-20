# OpenAlex Snapshot Fetcher

Pull small, targeted slices of the [OpenAlex](https://openalex.org) scholarly
graph snapshot from the public AWS bucket — works, authors, citations, journals,
institutions, topics, and more.

- **Bucket:** `s3://openalex` (us-east-1, public, anonymous access OK)
- **Registry:** https://registry.opendata.aws/openalex/
- **Docs:** https://docs.openalex.org/download-all-data/openalex-snapshot ·
  https://docs.openalex.org/api-entities/entities-overview
- **License:** CC0

> ⚠️ **Total size warning:** the full snapshot is ~**750 GB** compressed
> (~650 M records); the `works` entity alone is ~665 GB. Never sync whole
> entities — use the slice flags below. `fetch.py` refuses downloads above
> 5 GB by default (`--max-size-gb`).

## Bucket layout (verified against the live bucket)

```
s3://openalex/
├── LICENSE.txt / README.txt / RELEASE_NOTES.txt / browse.html
├── data/
│   ├── jsonl/                          ← what fetch.py uses
│   │   ├── manifest.json               ← global manifest (all entities)
│   │   └── {entity}/
│   │       ├── manifest.json           ← per-entity manifest
│   │       └── updated_date=YYYY-MM-DD/
│   │           └── part_NNNN.gz        ← gzipped JSON Lines
│   └── parquet/                        ← same tree, Parquet format
└── legacy-data/                        ← old snapshot layout
```

**Entities** (prefixes under `data/jsonl/`): `authors`, `awards`, `concepts`,
`continents`, `countries`, `domains`, `fields`, `funders`,
`institution-types`, `institutions`, `keywords`, `languages`, `licenses`,
`publishers`, `sdgs`, `source-types`, `sources`, `subfields`, `topics`,
`work-types`, `works`.

**Partitioning:** each entity is split into `updated_date=YYYY-MM-DD/`
partitions — a record lives in the partition matching the date it was last
updated. To get "everything" for an entity you need *all* partitions; to get
"what changed recently" you only need recent ones.

**Manifests:** `data/jsonl/{entity}/manifest.json` lists every part file with
its exact size and record count:

```json
{
  "date": "2026-06-26", "format": "jsonl", "entity": "concepts",
  "record_count": 123456, "content_length": 987654321,
  "files": [
    {"url": "s3://openalex/data/jsonl/concepts/updated_date=2026-06-26/part_0000.gz",
     "meta": {"content_length": 6388262, "record_count": 61055}}
  ]
}
```

`fetch.py` reads the manifest to plan slices — no bucket pagination needed.

## File format

Each `part_NNNN.gz` is a **gzip-compressed JSON Lines** file: one complete
entity object per line.

```python
import gzip, json
with gzip.open("part_0000.gz", "rt", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
```

### Key fields by entity

| Entity | Key fields |
|---|---|
| **works** | `id`, `doi`, `title`, `publication_year`, `authorships` (author + institutions per author), `primary_location` (source/journal), `cited_by_count`, `referenced_works` (outgoing citations), `related_works`, `topics`, `open_access`, `abstract_inverted_index` |
| **authors** | `id`, `orcid`, `display_name`, `works_count`, `cited_by_count`, `last_known_institutions`, `affiliations`, `summary_stats` (h-index etc.) |
| **sources** | `id`, `issn_l`, `display_name`, `host_organization`, `is_oa`, `works_count`, `type` (journal/repository/…) |
| **institutions** | `id`, `ror`, `display_name`, `country_code`, `type`, `works_count`, `associated_institutions`, `geo` |
| **topics** | `id`, `display_name`, `subfield`/`field`/`domain`, `keywords`, `works_count` |
| **publishers / funders** | `id`, `display_name`, `works_count`, `cited_by_count`, ids (`ror`, `wikidata`, …) |
| **concepts** | `id`, `wikidata`, `display_name`, `level`, `ancestors`, `related_concepts` (legacy tagging, superseded by topics) |

All records carry `id` (an `https://openalex.org/...` URL), `updated_date`,
and `created_date`. Citations are edges: `works.referenced_works` lists the
OpenAlex IDs a work cites, and `cited_by_count` is the incoming total. Full
schemas: https://docs.openalex.org/api-entities/entities-overview

## fetch.py

Requires Python 3.10+ and `boto3`. **On the HackMIT EC2 instances (Amazon
Linux 2023) you may need to install pip + boto3 first:**

```bash
sudo dnf install -y python3-pip && pip3 install boto3
```

Anonymous access is the default (no AWS credentials needed). On the EC2
instances you can also pass `--signed` to use the instance's
AmazonS3ReadOnlyAccess role — same-region S3 traffic is free and fast via the
gateway endpoint.

### How slice args map to S3 keys

| Flag | Effect on keys |
|---|---|
| `--entity E` (repeatable, or `all`) | selects `data/jsonl/E/...` (from the entity manifest) |
| `--updated-date YYYY-MM-DD` | only `updated_date=YYYY-MM-DD/` partitions |
| `--updated-since YYYY-MM-DD` | only partitions with `updated_date >=` that date |
| `--max-files N` | keep at most N part files **per entity**, newest partitions first |
| `--list` | print matching keys + sizes, download nothing |
| `--max-size-gb G` | refuse download if the slice exceeds G GB (default 5) |
| `--output-dir DIR` | destination root (default `./data/openalex`); files land in `DIR/{entity}/updated_date=…/part_NNNN.gz` plus `DIR/{entity}/manifest.json` |
| `--signed` | use AWS credentials/IAM role instead of anonymous |

Already-downloaded files with matching sizes are skipped, so re-runs are cheap.

### Examples

```bash
# Safe default: concepts manifest + its single most recent part file (~6 MB)
python fetch.py

# What would a slice cost? List keys + total size, download nothing:
python fetch.py --list --entity works --updated-since 2026-06-01

# Recent works, capped at 10 files:
python fetch.py --entity works --updated-since 2026-06-01 --max-files 10

# A couple of small entities in full:
python fetch.py --entity topics --entity funders

# One exact partition:
python fetch.py --entity authors --updated-date 2026-06-26 --max-files 5

# On EC2 with the IAM role:
python3 fetch.py --signed --entity sources --max-files 3
```
