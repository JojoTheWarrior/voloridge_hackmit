# M20260920-8242ae

| Field | Value |
|---|---|
| Mission id | `M20260920-8242ae` |
| Folder | `20260920-125-finance-ng-f-close_x_finance-bz-f-close` |
| Indicators | `finance.NG=F.close` × `finance.BZ=F.close` |
| n_obs | 390 |
| r | 0.11430253849373316 |
| Best lag | 0 (days) |
| perm_p | 0.2215568862275449 |
| Bonferroni | 1.0 |
| pre/post Δr | 0.25306796103068985 |
| Fisher p | 0.013053165674789398 |
| Scores | {'validity': 2.12, 'interestingness': 3.76, 'unexpectedness': 4.82, 'supported_prob': 0.76, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.NG=F.close` (configured analysis window); `finance.BZ=F.close` (configured analysis window) |

## Research note: Henry Hub vs Brent daily returns as a fuel-switching proxy

**1. Verdict:** Weakly supported, and only for the proxy — the Henry Hub–Brent daily-return correlation rose from r = 0.07 (pre-war, n = 250) to r = 0.32 (post-war, n = 140; Fisher-z p = 0.013), but the full-sample permutation p is 0.22 and the hypothesis itself (EIA-923 petroleum-fired generation) was never tested.

**2. What the data shows.** n = 390 daily observations (2025-03-04 to 2026-09-18), both series as pct_change. Full-sample Pearson r = 0.11 (p = 0.024), Spearman 0.14 (p = 0.004). Best lag is 0 of 15 tested (±7 days), so there is no evidence gas leads oil; Bonferroni-adjusted p = 1.0. The signal lives almost entirely in the post-2026-02-28 window, where co-movement is roughly 4–5x the pre-war level. No event study was run. Sign matches expectation, but a rising cross-commodity correlation says nothing directly about petroleum-fired MWh.

**3. Confounders and caveats.** (a) Wrong response variable: the catalogue truncation forced a price-price substitute; EIA-923 petroleum generation (monthly, freq=M) is absent. (b) The war is a common shock to both energy benchmarks — higher co-movement in a crisis is the default expectation for all risk assets, not evidence of fuel switching. (c) Post-war n = 140 with a volatility regime change; Pearson on fat-tailed returns is fragile, and the zero-lag result is consistent with same-day macro news. (d) US petroleum generation is tiny (~0.5% of output), seasonal (winter/summer peaks) and driven by regional gas constraints (New England, Hawaii), not Brent.

**4. Follow-up.** Pull `pudl.eia923.petroleum_liquids_net_generation_mwh` (freq=M) and `pudl.eia930` hourly fuel mix; run a single-mode pre/post comparison of March–April 2026 vs the same months in 2025 (Welch t, effect size), plus a control on gas-fired generation.
