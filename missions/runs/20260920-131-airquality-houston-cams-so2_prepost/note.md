# M20260920-99b24e

| Field | Value |
|---|---|
| Mission id | `M20260920-99b24e` |
| Folder | `20260920-131-airquality-houston-cams-so2_prepost` |
| Indicators | `airquality.houston.cams_so2` |
| n_obs | 566 |
| r |  |
| Best lag | n/a (days) |
| perm_p | 0.07784431137724551 |
| Bonferroni | 0.07784431137724551 |
| pre/post mean Δ | -0.415753420613824 |
| Welch p | 1.4399676226957944e-06 |
| Scores | {'validity': 4.0, 'interestingness': 2.88, 'unexpectedness': 9.6, 'supported_prob': 0.02, 'judge_model': 'jev-1.13.0'} |
| Data sources | `airquality.houston.cams_so2` (2025-03..2026-09 archive window) |

## Houston CAMS SO₂ anomaly, pre- vs post-war (single-mode)

**Verdict: not supported.** The Houston SO₂ anomaly *fell* after 2026-02-28 (mean difference −0.42 SD, Cohen's d = −0.42), the opposite of the expected rise.

**What the data shows.** n = 566 daily obs (2025-03-01 → 2026-09-17). Pre-war mean anomaly +0.04 (n = 364, sd 1.02); war-period mean −0.37 (n = 202, sd 0.94). Welch t = 4.89, p ≈ 1.4e-6, but the permutation p is 0.078 — the gap between the two suggests strong day-to-day autocorrelation inflates the parametric test; treat the drop as moderate, not decisive. No lag or correlation was tested (same series both sides).

**Confounders and caveats.**
- *Baseline circularity:* the anomaly is computed against the same-week 2025 baseline, so the pre-war segment is largely the baseline itself and is ~0 by construction; the "post" mean really measures 2026 vs 2025, mixing war effects with any secular 2025→2026 trend (e.g. EPA/TCEQ SO₂ controls, refinery turnarounds, fuel-sulfur changes).
- *CAMS is a model reanalysis* driven by fixed emission inventories; it would not register a real throughput ramp unless satellite assimilation catches it. A null or negative result here says little about actual stack emissions.
- Unequal, short post window (202 days) spanning ceasefire, reopening and renewed tanker war — regime heterogeneity averaged away.
- Meteorology (2026 spring ventilation/rain) can dominate surface SO₂.

**Follow-up.** Swap CAMS for OpenAQ ground monitors (Houston Ship Channel SO₂/NO₂) and pair with PUDL/EIA-923 Gulf Coast petroleum-coke or refinery-gas generation as a throughput proxy, with an event study around 2026-03-04 and 2026-07-08.
