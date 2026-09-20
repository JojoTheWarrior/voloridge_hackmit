# M20260920-1cf78d

| Field | Value |
|---|---|
| Mission id | `M20260920-1cf78d` |
| Folder | `20260920-132-utility-fuel-cost-oil-per-mmbtu_x_utility-fuel-cost-gas-per-mmbtu` |
| Indicators | `utility.fuel_cost.oil_per_mmbtu` × `utility.fuel_cost.gas_per_mmbtu` |
| n_obs | 14 |
| r | -0.12041051966121964 |
| Best lag | 1 (months) |
| perm_p | 0.2215568862275449 |
| Bonferroni | 0.6646706586826348 |
| pre/post Δr | -1.238464398052216 |
| Fisher p |  |
| Scores | {'validity': 2.02, 'interestingness': 1.62, 'unexpectedness': 6.32, 'supported_prob': 0.02, 'judge_model': 'jev-1.13.0'} |
| Data sources | `utility.fuel_cost.oil_per_mmbtu` (configured analysis window); `utility.fuel_cost.gas_per_mmbtu` (configured analysis window) |

## Research note: oil vs gas delivered fuel cost (monthly pct_change), pre/post-war

**1. Verdict — not supported / inconclusive.** Contemporaneous Pearson r = −0.12 (p = 0.68, n = 14); the best 1-month lead is *negative* (r = −0.53), opposite to the expected positive sign, and the permutation p = 0.22 (Bonferroni 0.66) is not significant.

**2. What the data shows.** Coverage 2025-04 to 2026-05, 14 monthly observations (freq=M). Spearman r = −0.29 (p = 0.32). Lags tested: 0–1 month (3 tests). Pre-war (n = 11): r = +0.24 (p = 0.47), Spearman ≈ 0. Post-war (n = 3): r = −0.997 (p = 0.049), Spearman = −1. The r change of −1.24 is computed on three points; the Fisher-z test is undefined at this n. The war-period result is essentially a line through three dots and cannot speak to a change in lag structure — no lag comparison is possible with three post-war months.

**3. Confounders and caveats.** (a) This is not the hypothesised test: no Henry Hub series exists in the catalogue, so oil delivered cost is a stand-in for the upstream gas benchmark — oil and gas delivered costs need not co-move at all. (b) Delivered costs are contract-lagged, volume-weighted averages (EIA-923), smoothing spot shocks over several months. (c) The war and Hormuz closure are a common cause of both series; any post-war association is likely spurious trend-sharing. (d) Seasonality (winter gas demand) drives gas cost independently of oil. (e) Very small n, plus multiple testing.

**4. Follow-up.** Ingest Henry Hub (FRED: DHHNGSP) and WTI/Brent daily, then test daily Brent → monthly EIA-923 gas cost with 0–3-month leads, adding 2024 baseline months to raise n.
