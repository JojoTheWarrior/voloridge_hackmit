# M20260920-a64ade

| Field | Value |
|---|---|
| Mission id | `M20260920-a64ade` |
| Folder | `20260920-123-airquality-tehran-cams-no2_prepost` |
| Indicators | `airquality.tehran.cams_no2` |
| n_obs | 566 |
| r |  |
| Best lag | n/a (days) |
| perm_p | 0.5828343313373253 |
| Bonferroni | 0.5828343313373253 |
| pre/post mean Δ | 2.5418173375281214 |
| Welch p | 0.01538961142422776 |
| Scores | {'validity': 0.12, 'interestingness': 2.42, 'unexpectedness': 7.96, 'supported_prob': 0.03, 'judge_model': 'jev-1.13.0'} |
| Data sources | `airquality.tehran.cams_no2` (2025-03..2026-09 archive window) |

## Research note: Iranian scholarly output during the war

**1. Verdict — Inconclusive.** The target series (Iran-affiliated OpenAlex publication counts) was not in the catalogue, so the plan tested a stand-in (Tehran CAMS NO2 anomaly) that cannot speak to publication output. The proxy moved *opposite* to the expected sign (post-war anomaly +2.54 units higher; permutation p = 0.58).

**2. What the data shows (proxy only).** Single-mode comparison, n = 566 daily obs (2025-03-01 to 2026-09-17). Pre-war NO2 anomaly mean 0.05 (n = 104, sd 9.2) vs post-war 2.59 (n = 462, sd 10.9); mean difference +2.54, Welch t = −2.45, p = 0.015, Cohen's d = 0.24 (small). The permutation test does not confirm it (p = 0.58; Bonferroni-adjusted 0.58). Event study around 20 war events: mean anomaly −0.96 pre vs −5.03 post, change −4.07, t = −1.74, p = 0.097 — directionally negative but not significant, and inconsistent with the pre/post rise.

**3. Confounders and caveats.** The proxy is conceptually unrelated to research output; an NO2 anomaly reflects traffic, fuel switching, blackouts, wildfire/dust and CAMS model revisions, not connectivity or publishing. Pre/post groups are badly unbalanced (104 vs 462 days), and the anomaly baseline is derived from the same short 2025 window, so seasonality is only partly removed. Autocorrelated daily data inflate Welch significance, which is why the permutation p disagrees. Post-period spans three regimes (war, ceasefire, renewed tanker war). Nothing here bears on the hypothesis.

**4. Follow-up.** Ingest OpenAlex monthly (freq=M) works by Iranian institution ID, compare Mar–Jun 2026 vs the same months in 2025, and pair with an internet-outage index (IODA/Cloudflare radar) and a non-Iranian regional control (Turkey, Pakistan) for a difference-in-differences design.
