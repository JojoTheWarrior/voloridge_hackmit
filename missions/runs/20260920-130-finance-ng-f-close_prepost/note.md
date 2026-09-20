# M20260920-8f068d

| Field | Value |
|---|---|
| Mission id | `M20260920-8f068d` |
| Folder | `20260920-130-finance-ng-f-close_prepost` |
| Indicators | `finance.NG=F.close` |
| n_obs | 390 |
| r |  |
| Best lag | n/a (days) |
| perm_p | 0.9600798403193613 |
| Bonferroni | 0.9600798403193613 |
| pre/post mean Δ | -0.00015545322660911093 |
| Welch p | 0.9725189857304888 |
| Scores | {'validity': 0.0, 'interestingness': 0.46, 'unexpectedness': 4.48, 'supported_prob': 0.02, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.NG=F.close` (configured analysis window) |

## Research note: coal share vs Henry Hub after March 2026

**1) Verdict — inconclusive.** The coal-share leg was never tested: the plan degenerated to Henry Hub (NG=F) against itself in single mode, and even the gas leg shows no pre/post shift (Welch p = 0.97).

**2) What the data shows.** n = 390 daily observations (2025-03-04 to 2026-09-18) of NG=F daily percent change. Pre-war (n = 250) mean +0.06%/day, SD 6.2%; post-war (n = 140) mean +0.05%/day, SD 2.6%. Mean difference −0.0002 (Cohen's d ≈ −0.003), Welch t = 0.03, p = 0.97; permutation p = 0.96 (no lag search, so Bonferroni is moot). Notably, post-war *volatility* fell by more than half, the opposite of a "gas price spike" narrative — the Hormuz closure is a crude/LNG-export shock, and US Henry Hub is largely insulated from seaborne LNG pricing. No correlation, lag or event-study effect exists to report because indicator_b was not a coal series.

**3) Confounders and caveats.** Daily returns are near-zero-mean by construction, so a mean test on pct_change cannot detect a level shift; a level or log-level comparison was needed. Any future coal-share test (freq=M) will have n ≈ 6–7 post-war months: seasonality (summer peak load, spring hydro, shoulder-month maintenance), pre-existing coal-retirement trends, and 2025–26 gas storage levels dominate dispatch. A nominally "significant" monthly result after multiple lag testing would be very fragile.

**4) Follow-up.** Re-run as dual mode: indicator_a = NG=F level (or monthly mean), indicator_b = PUDL EIA-923/930 monthly coal share of net generation (freq=M), lag 0–2 months, with a seasonal difference (same month, prior year) and a null control such as ERCOT wind share.
