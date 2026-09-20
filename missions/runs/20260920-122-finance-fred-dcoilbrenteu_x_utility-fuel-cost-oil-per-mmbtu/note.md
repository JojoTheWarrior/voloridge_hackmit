# M20260920-83e523

| Field | Value |
|---|---|
| Mission id | `M20260920-83e523` |
| Folder | `20260920-122-finance-fred-dcoilbrenteu_x_utility-fuel-cost-oil-per-mmbtu` |
| Indicators | `finance.fred.DCOILBRENTEU` × `utility.fuel_cost.oil_per_mmbtu` |
| n_obs | 14 |
| r | 0.7320426706644398 |
| Best lag | 0 (months) |
| perm_p | 0.08782435129740519 |
| Bonferroni | 0.2634730538922156 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 4.0, 'interestingness': 3.8, 'unexpectedness': 3.04, 'supported_prob': 0.05, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.fred.DCOILBRENTEU` (configured analysis window); `utility.fuel_cost.oil_per_mmbtu` (configured analysis window) |

**Verdict: weakly supported.** The contemporaneous association is sizeable (Pearson *r* = 0.732), but is not robust to the permutation test (*p* = 0.088; Bonferroni-adjusted *p* = 0.263).

**What the data shows.** Across 14 monthly observations from 2025-04-01 through 2026-05-01, monthly percentage changes in Brent and petroleum-liquids fuel receipt cost move together positively (Pearson *r* = 0.732, *p* = 0.0029; Spearman ρ = 0.666, *p* = 0.0093). The best tested lag is 0 months, not a delayed pass-through below one month. Pre/post-war means and an event-study effect were not computed, so no war-period shift can be claimed.

**Caveats.** The sample is very small and the fuel-cost series ends before the later war milestones. Monthly aggregation cannot resolve sub-month timing; receipt costs may reflect contracts, inventory, reporting delays, and plant-level fuel mix. Seasonality, shared exposure to the war and global energy markets, Brent’s extreme spike, autocorrelation, and multiple lag/relationship searches can inflate apparent significance. Correlation does not establish pass-through or causation.

**Follow-up mission.** Extend EIA-923 fuel-cost coverage and compare plant-level petroleum-liquid costs with Brent using weekly or transaction-timed data, explicitly testing contract/reporting lags and a non-war oil benchmark.
