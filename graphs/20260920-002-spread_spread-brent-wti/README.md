# Brent–WTI Crude Oil Spread

- prompt: brent-WTI spread
- chart_type: spread
- codegen: template
- folder: 20260920-002-spread_spread-brent-wti

## Series

- `finance.spread.brent_wti` — finance.spread.brent_wti (2025-01-02..2026-09-18, n=431)

Notes: Uses the precomputed finance.spread.brent_wti series (Brent minus WTI) over the configured analysis window.
Rationale: The prompt explicitly asks for the Brent–WTI spread, and the catalogue already includes a dedicated spread series finance.spread.brent_wti, which should be plotted as a spread chart rather than recomputing from Brent and WTI components.

Files: `plan.json`, `prompt.txt`, `chart.py`, `data/*.csv`, `iran_timeline.csv`, `thumbnail.png`.