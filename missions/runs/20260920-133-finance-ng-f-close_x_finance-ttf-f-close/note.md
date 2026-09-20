# M20260920-47ce02

| Field | Value |
|---|---|
| Mission id | `M20260920-47ce02` |
| Folder | `20260920-133-finance-ng-f-close_x_finance-ttf-f-close` |
| Indicators | `finance.NG=F.close` × `finance.TTF=F.close` |
| n_obs | 390 |
| r | 0.12524741482200136 |
| Best lag | 28 (days) |
| perm_p | 0.04790419161676647 |
| Bonferroni | 1.0 |
| pre/post Δr | 0.2378939743106942 |
| Fisher p | 0.01910599415641115 |
| Scores | {'validity': 6.0, 'interestingness': 3.78, 'unexpectedness': 6.76, 'supported_prob': 0.87, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.NG=F.close` (configured analysis window); `finance.TTF=F.close` (configured analysis window) |

## Research note: Henry Hub vs. TTF daily returns, pre/post war

**Verdict: inconclusive for the stated hypothesis; the proxy result runs opposite to it.** The Henry Hub–TTF return correlation *rose* after 2026‑02‑28 (r 0.08 → 0.32, Fisher z p = 0.019), i.e. the available proxy shows tighter, not looser, linkage.

**What the data shows.** n = 390 trading days (2025‑03‑04 to 2026‑09‑18), daily pct_change of NG=F and TTF=F. Full-sample Pearson r = 0.13 (p = 0.013), Spearman 0.10 (p = 0.05). Best lag = 28 days (r = 0.23), but 61 lags were scanned: Bonferroni p = 1.0 and permutation p = 0.048 — a borderline result that should not be read as monthly contract pass-through. Pre-war (n = 250): r = 0.08, n.s.; post-war (n = 140): r = 0.32 (p = 1e‑4), Spearman 0.28. r_change = +0.24.

**Confounders and caveats.** (1) TTF is a European hub price, not EIA‑923 delivered fuel cost at US plants; the test does not touch contract stickiness at all. (2) The war is a common cause: Hormuz closure hit LNG (Qatar) and oil-linked gas simultaneously, mechanically raising global gas co-movement — a regime of shared volatility, not a pass-through change. (3) Post window (140 days) spans several distinct sub-regimes (closure, ceasefire, reopening, renewed tanker war); heteroskedasticity inflates Pearson r. (4) The 28‑day lag is one of 61 tests and survives no correction. (5) Seasonality (winter 2025/26 heating demand) overlaps the post window.

**Follow-up.** Pull the actual PUDL EIA‑923 monthly gas fuel cost ($/MMBtu, freq=M) and regress its monthly change on same-month and 1‑month-lagged Henry Hub, comparing residual variance 2025 vs. 2026 — a single-mode pre/post test of the stickiness claim itself, ideally with TTF as a control regressor.
