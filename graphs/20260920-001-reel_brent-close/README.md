# Brent Crude Futures (BZ=F) Daily Close

- prompt: the instagram reels of the price of brent
- chart_type: reel
- codegen: template
- folder: 20260920-001-reel_brent-close

## Series

- `finance.BZ=F.close` — BZ=F close (2025-01-02..2026-09-18, n=431)

Notes: Use vertical (9:16) layout and animate the time axis to suit Instagram Reels. Focus on the 2025-01-02..2026-09-18 window where BZ=F coverage is available. Optionally highlight major price spikes with labels tied to Iran/Hormuz events for narrative context.
Rationale: User explicitly requested an Instagram-style reel of Brent prices. The best in-catalogue proxy is Brent crude futures daily close (finance.BZ=F.close), which directly represents Brent pricing and has suitable recent coverage. A reel chart type fits the requested social-video format, with a single animated time-series line.

Files: `plan.json`, `prompt.txt`, `chart.py`, `data/*.csv`, `iran_timeline.csv`, `thumbnail.png`.