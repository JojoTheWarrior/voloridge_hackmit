# Materials Project — AWS OpenData fetcher

Pull slices of the [Materials Project](https://materialsproject.org/) open dataset
(computed materials properties) from its public S3 buckets in **us-east-1** — the same
region as your HackMIT EC2 instance, so transfers are free and fast.

- Registry: <https://registry.opendata.aws/materials-project/>
- Official docs: <https://docs.materialsproject.org> (see
  [AWS OpenData](https://docs.materialsproject.org/downloading-data/aws-opendata))

## Buckets

| Bucket | ARN | Contents |
|---|---|---|
| `materialsproject-build` | `arn:aws:s3:::materialsproject-build` | **Build data** (default): high-level document collections as gzipped JSONL — this is what you almost certainly want |
| `materialsproject-parsed` | `arn:aws:s3:::materialsproject-parsed` | **Parsed data**: parsed VASP calculation outputs — `tasks_atomate2/`, `tasks-legacy/`, `bandstructures/`, `dos/`, `chgcars/`, `elfcars/`, `locpots/`, `phonon/`, `defects/`, ... (large binary-ish payloads) |
| `materialsproject-raw` | `arn:aws:s3:::materialsproject-raw` | **Raw data**: only a top-level `openmetadata_storage_manifest.json` is publicly listed |

## Build-bucket layout (verified 2026-09)

Dated snapshots live under `collections/<YYYY-MM-DD>/<collection>/`:

```
collections/2025-09-25/
├── materials/                       # core structure + calculation metadata
│   ├── manifest.jsonl.gz            # per-doc index for the collection
│   └── nelements=1/ ... nelements=9/            # Hive-style partitioning
│       └── symmetry_number=<spacegroup>.jsonl.gz
├── thermo/                          # thermodynamics, extra partition level:
│   └── thermo_type={GGA_GGA+U, GGA_GGA+U_R2SCAN, R2SCAN}/nelements=N/...
├── summary/                         # one-stop aggregated docs; flat list of
│   └── <uuid>.jsonl.gz              # ~10–50 MB chunks (no Hive partitions)
├── elasticity/ dielectric/ piezoelectric/ magnetism/ bonds/ chemenv/
├── electronic-structure/ insertion-electrodes/ conversion-electrodes/
├── absorption/ alloys/ oxi-states/ phonon/ provenance/ robocrys/ ...
```

There are also non-dated collection dirs at `collections/<name>/` (Delta-Lake style
`version=.../` + `_delta_log/`) and `static-collections/`, `current-build/`, `objects/`
prefixes. The fetch script defaults to the newest dated snapshot.

## File format

Every collection file is **gzipped JSONL**: one JSON document per line.

```python
import gzip, json
with gzip.open("symmetry_number=225.jsonl.gz", "rt") as f:
    docs = [json.loads(line) for line in f]
```

Key fields of the main collections:

- **materials**: `material_id` (e.g. `mp-1096992`), `formula_pretty`, `elements`,
  `chemsys`, `nelements`, `nsites`, `composition`, `structure` (pymatgen-serialized
  lattice + sites), `symmetry` (space group), `entries` (computed energies per run
  type), `density`, `volume`, `task_ids`, `deprecated`, `builder_meta`
- **thermo**: `material_id`, formation energy / energy above hull per `thermo_type`,
  decomposition info
- **summary**: aggregated "everything" doc per material — `material_id`, formula,
  `band_gap`, `formation_energy_per_atom`, `energy_above_hull`, `is_stable`, elastic /
  dielectric / magnetic properties, `structure`, ...

`structure` fields deserialize with [pymatgen](https://pymatgen.org/):
`Structure.from_dict(doc["structure"])`.

## Usage

```bash
python fetch.py [options]
```

| Arg | Meaning |
|---|---|
| `--output-dir` | destination (default `./data/materials_project`); files land under `<output-dir>/<bucket>/<key>` |
| `--bucket` | `materialsproject-build` (default) / `-parsed` / `-raw` |
| `--collection NAME` | repeatable; maps to `collections/<snapshot>/<NAME>/` in the build bucket, or `<NAME>/` in the parsed bucket |
| `--snapshot YYYY-MM-DD` | build snapshot date (default: newest dated snapshot) |
| `--prefix` | free-form key prefix override, e.g. `collections/2025-09-25/materials/nelements=2/` |
| `--max-files N` | cap file count per collection/prefix |
| `--max-size-gb` | safety cap (default 5); refuses larger slices |
| `--list` | show matching keys + total size, no download |
| `--list-collections` | enumerate collections in the chosen bucket |
| `--signed` | use AWS credentials instead of anonymous access |

**Default (no args)** downloads a small demo slice: the `materials` collection,
`nelements=1/` partition (~2.7 MB, ~90 files). It never downloads whole buckets.

### Examples

```bash
# What collections exist?
python fetch.py --list-collections

# Preview a slice (no download): all 3-element materials docs
python fetch.py --collection materials --prefix collections/2025-09-25/materials/nelements=3/ --list

# Small demo download (default slice)
python fetch.py

# First 5 files of the thermo collection
python fetch.py --collection thermo --max-files 5

# R2SCAN thermo docs for unary systems
python fetch.py --prefix "collections/2025-09-25/thermo/thermo_type=R2SCAN/nelements=1/"

# One summary chunk (each is 10–50 MB)
python fetch.py --collection summary --max-files 1

# Parsed bucket: peek at atomate2 task layout
python fetch.py --bucket materialsproject-parsed --list-collections
```

## Running on your EC2 instance (Amazon Linux 2023)

The instance role is S3-read-only and there is an S3 gateway endpoint, so same-region
access is free. Install boto3 first:

```bash
sudo dnf install -y python3-pip
pip3 install boto3
# optional, to work with structures as objects:
pip3 install pymatgen
```

Then `python3 fetch.py ...` as above. Anonymous access (default) works both on and
off EC2; `--signed` uses the instance role / your credentials.
