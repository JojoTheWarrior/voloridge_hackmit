# Research snapshot

Code, notes, results and figures from the team's research directory
(`explore/`, kept next to this repo and not under version control). The
21 GB of data behind them is deliberately left out; this folder is about 40 MB.

Start with `IDEAS.md`. It is the running record: every idea, what was
tested, and the verdict in the heading (VERIFIED, MIXED, DOWNGRADED, REJECTED,
DEAD), including the nulls. The statuses below are copied from it as of this
snapshot; when they disagree, `IDEAS.md` wins.

| Folder | `IDEAS.md` section | Status there |
| --- | --- | --- |
| `dams/` | 1, 1b, 1c. Dams from space → hydropower / blackout nowcast | Verified (univariate); at scale "real but modest, not an early warning" |
| `wardamage/` | 2, 2b, 3. Gulf gas flaring as a production gauge; strike detection | Verified, then downgraded to "outage alarm, not a gauge"; strikes partial |
| `powerplants/` | 4, 4b. Power plants from space (NO2 / steam plumes vs EPA CEMS) | Verified, weak-to-moderate; "relative signals hold, levels don't" |
| `airquality/` | 5. PM2.5 in cities with no monitors | Original pitch dead; negative result usable |
| `markets/` | 10. Do orbit-measured signals predict market prices? | Rejected (rigorous null); sensor validated |
| `scout/` | Scouting runs behind several sections (dams round 2, blackouts, grid tests) | Mixed |
| `fixlist_methane/`, `fixlist_flares/`, `fixlist_darkclinics/`, `fixlist_zonezero/`, `fixlist_tarps/` | The search for an "asbestos-grade" actionable finding (top of the file) | Running |
| `polymarket/`, `polymarket_experts/` | Not in `IDEAS.md`; see `REPORT.md` in each, and `CODEX_BRIEFS.md` for the briefs they ran from | — |

Where the work got far enough, a folder has a `findings.json` written for the
frontend (`dams`, `wardamage`, `powerplants`, `markets`, and both Polymarket
folders).

## What is not here

Anything that is data rather than a finding: `data/`, `cache/` and similar
folders, satellite tiles, parquet, zip and array files, scraped text, trained
models, virtualenvs, and any single file over 1.5 MB (city lists, location
indexes and other inputs that can be downloaded again). The exact rules are in
`.snapshot-filter`. The scripts expect those inputs under their own `data/` or
`cache/` folder and will re-fetch most of them.

## Refreshing it

```bash
research/sync_from_explore.sh            # from ../explore
research/sync_from_explore.sh /some/path # or from anywhere else
```

It mirrors the source, so files removed there are removed here; this README,
the script and the filter are kept.
