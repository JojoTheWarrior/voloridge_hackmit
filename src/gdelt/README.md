# GDELT — Global Database of Events, Language and Tone

Global news event data: who did what to whom, where, when, and with what tone,
extracted from worldwide news coverage.

- **Registry:** https://registry.opendata.aws/gdelt/
- **Bucket:** `s3://gdelt-open-data` (us-east-1, public — anonymous access works)
- **Status:** the bucket is **no longer updated** (v1 ends 2019-09-18, v2 ends 2019-04-16)
- **Project site / docs:** https://www.gdeltproject.org/data.html

## Bucket layout (verified against the live bucket)

```
s3://gdelt-open-data/
├── events/                      # GDELT v1 events
│   ├── 1979.csv … 2005.csv          yearly files (1979–2005)
│   ├── 200601.csv … 201303.csv      monthly files (2006-01 – 2013-03)
│   └── 20130401.export.csv …        daily files (2013-04-01 – 2019-09-18)
│       20190918.export.csv
└── v2/                          # GDELT v2, one file every 15 minutes
    ├── events/YYYYMMDDHHMMSS.export.csv
    ├── mentions/YYYYMMDDHHMMSS.mentions.csv
    └── gkg/YYYYMMDDHHMMSS.gkg.csv
        # coverage: 2015-02-18 23:00:00 UTC – 2019-04-16 15:15:00 UTC
        # 96 files per table per full day (00:00, 00:15, …, 23:45)
```

## File format

All files are **tab-separated values (TSV)** despite the `.csv` extension, with
**NO header row**. UTF-8 (v1 older files are ASCII/latin-1-ish; treat as UTF-8
with `errors="replace"` if needed).

Column counts (verified on real files):

| Table | Columns | Codebook |
|---|---|---|
| v2 events | 61 | [GDELT-Event_Codebook-V2.0.pdf](http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf) |
| v2 mentions | 16 | same codebook (mentions section) |
| v2 gkg | 27 | [GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf](http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf) |
| v1 events (daily) | 58 | [GDELT Data Format Codebook v1](http://data.gdeltproject.org/documentation/GDELT-Data_Format_Codebook.pdf) |

### Key columns of the events table (v2, 0-indexed)

| # | Column | Meaning |
|---|---|---|
| 0 | `GlobalEventID` | unique event id |
| 1 | `Day` | event date, YYYYMMDD |
| 5 | `Actor1Code` | CAMEO code for actor 1 (also Name, CountryCode, … in cols 6–14) |
| 15 | `Actor2Code` | CAMEO code for actor 2 (cols 16–24 mirror actor 1) |
| 26 | `EventCode` | CAMEO action code (what was done) |
| 29 | `QuadClass` | 1=verbal coop, 2=material coop, 3=verbal conflict, 4=material conflict |
| 30 | `GoldsteinScale` | −10…+10 conflict/cooperation intensity |
| 31 | `NumMentions` | number of mentions of this event |
| 34 | `AvgTone` | average tone of covering documents (−100…+100, typically −10…+10) |
| 53 | `ActionGeo_FullName` | resolved location of the event |
| 56 | `ActionGeo_Lat` | latitude |
| 57 | `ActionGeo_Long` | longitude |
| 59 | `DATEADDED` | YYYYMMDDHHMMSS the event was added |
| 60 | `SOURCEURL` | URL of the first news report |

(There are also `Actor1Geo_*` (cols 35–42) and `Actor2Geo_*` (cols 44–51) location blocks.
See the codebook for the full 61-column list. v1 daily files use the same schema minus the
mentions-era additions: 58 columns, ending at `DATEADDED`/`SOURCEURL`.)

### Mentions table (v2 only, 16 cols)

One row per *mention* of an event in an article: `GlobalEventID`, `EventTimeDate`,
`MentionTimeDate`, `MentionType`, `MentionSourceName`, `MentionIdentifier` (URL),
sentence/char offsets, `Confidence`, `MentionDocTone`, … Useful for tracking how
coverage of a single event spreads over time.

### GKG table (v2 only, 27 cols)

The Global Knowledge Graph: one row per news document with extracted themes,
persons, organizations, locations, counts, tone block (`V2Tone`), quotes, and
images. Fields are nested (semicolon/hash-delimited within a tab column) — read
the GKG codebook before parsing.

## fetch.py

Requires Python 3.10+ and `boto3`. **On the HackMIT EC2 instances (Amazon Linux
2023) you may need to install it first:**

```bash
sudo dnf install -y python3-pip && pip3 install boto3
```

Anonymous (unsigned) S3 access is used by default; pass `--signed` to use the
instance role / your AWS credentials instead.

### Slice arguments → S3 keys

| Arg | Effect |
|---|---|
| `--table events\|mentions\|gkg` | picks `v2/<table>/` (mentions/gkg are v2-only) |
| `--version 1\|2` (default 2) | v1 uses `events/YYYYMMDD.export.csv` daily files |
| `--start-date` / `--end-date` (YYYYMMDD) | inclusive day range; for v2 matches **all** 15-minute files whose timestamp falls on those days |
| `--list` | print matching keys + total size, download nothing |
| `--max-size-gb` (default 5) | refuse download if the slice is bigger than this |
| `--output-dir` (default `./data/gdelt`) | where files land (flat, by filename) |
| `--signed` | use AWS credentials instead of anonymous access |

With **no arguments** it downloads one recent day of v2 events (2019-04-15,
~96 files, ≈70 MB) — never the whole dataset. Already-downloaded files with
matching size are skipped, so re-runs are cheap.

Note: `--version 1` only handles the daily files (2013-04-01 – 2019-09-18).
The older yearly/monthly v1 files are not covered by the date-slice CLI —
grab them directly, e.g. `aws s3 cp --no-sign-request s3://gdelt-open-data/events/2001.csv .`

### Examples

```bash
# See what one day of v2 events looks like (no download)
python3 fetch.py --list --start-date 20190415

# One day of v2 events (the default)
python3 fetch.py

# A week of v2 mentions
python3 fetch.py --table mentions --start-date 20180101 --end-date 20180107

# GKG for a single day (big! list first)
python3 fetch.py --table gkg --start-date 20180101 --list

# v1 daily events for the last week of coverage
python3 fetch.py --version 1 --start-date 20190912 --end-date 20190918

# Load a file in Python
python3 -c "
import csv
with open('data/gdelt/20190415000000.export.csv', encoding='utf-8', errors='replace') as f:
    for row in csv.reader(f, delimiter='\t'):
        print(row[0], row[1], row[26], row[30], row[34], row[60]); break
"
```

## Codebook links

- v2 Events: http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
- v2 GKG: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
- v1 Events: http://data.gdeltproject.org/documentation/GDELT-Data_Format_Codebook.pdf
- CAMEO event codes: https://www.gdeltproject.org/data.html#documentation
