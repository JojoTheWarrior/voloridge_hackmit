# M20260920-12250f

| Field | Value |
|---|---|
| Mission id | `M20260920-12250f` |
| Folder | `20260920-124-airquality-dubai-cams-aod_x_utility-generation-solar-mwh` |
| Indicators | `airquality.dubai.cams_aod` × `utility.generation.solar_mwh` |
| n_obs | 14 |
| r | 0.24036148207495922 |
| Best lag | 0 (months) |
| perm_p | 0.26746506986027946 |
| Bonferroni | 0.26746506986027946 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 2.0, 'interestingness': 2.4, 'unexpectedness': 0.46, 'supported_prob': 0.05, 'judge_model': 'jev-1.13.0'} |
| Data sources | `airquality.dubai.cams_aod` (2025-03..2026-09 archive window); `utility.generation.solar_mwh` (configured analysis window) |

**Verdict: not supported** — the null-control pairing shows only a weak positive association (Pearson r = 0.24, permutation p = 0.267).

**What the data shows.** Across 14 monthly observations from 2025-04-01 to 2026-05-01, Pearson r = 0.240 (p = 0.408) and Spearman ρ = 0.310 (p = 0.281). The best—and only—tested lag was 0 months (r = 0.240); the Bonferroni-adjusted permutation p-value remains 0.267. No pre/post-war or event-study estimate was computed, so there is no measured change around the conflict milestones.

**Caveats.** This is not the specified Open-Meteo shortwave-radiation series: CAMS Dubai aerosol optical depth is an indirect atmospheric proxy, while monthly US solar generation is geographically and physically distinct. The sample is very small, monthly aggregation obscures timing, and percentage changes can amplify noise. Seasonality, annual trends, weather regimes, US generation mix changes, and the war itself could confound any shared movement; the proxy substitution and other catalogue searches also raise multiple-testing concerns. Correlation does not establish causation.

**Follow-up mission.** Re-run with matched daily Gulf shortwave-radiation observations and daily US solar proxies, then test whether the relationship survives seasonal adjustment and placebo war-event windows.
