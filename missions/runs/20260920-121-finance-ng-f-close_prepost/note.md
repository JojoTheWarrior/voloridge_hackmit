# M20260920-56bf68

| Field | Value |
|---|---|
| Mission id | `M20260920-56bf68` |
| Folder | `20260920-121-finance-ng-f-close_prepost` |
| Indicators | `finance.NG=F.close` |
| n_obs | 391 |
| r |  |
| Best lag | n/a (days) |
| perm_p | 0.013972055888223553 |
| Bonferroni | 0.013972055888223553 |
| pre/post mean Δ | -0.690715191570547 |
| Welch p | 4.4130165660698386e-38 |
| Scores | {'validity': 6.64, 'interestingness': 2.82, 'unexpectedness': 8.86, 'supported_prob': 0.03, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.NG=F.close` (configured analysis window) |

## Research note: 2026 generator-mix shift (gas/storage) — Henry Hub proxy

**1) Verdict:** Inconclusive for the actual question and *not supported* for the proxy: Henry Hub front-month fell after the war began (mean 3.62 → 2.93 $/MMBtu, Δ = −0.69), the opposite of the expected sign.

**2) What the data shows (single-mode, pre/post only):**
- n = 391 daily closes (2025-03-03 → 2026-09-18); pre-war n = 251, post-war n = 140.
- Pre mean 3.62 (sd 0.69); post mean 2.93 (sd 0.20); mean difference −0.69.
- Welch t = 14.8, p ≈ 4e-38; Cohen's d = −1.22 (large). Permutation p = 0.014 (Bonferroni-adjusted 0.014; only one test).
- No correlation or lag is reported: indicator_a and indicator_b are the same series, so any r would be trivially 1.0 and meaningless.

**3) Confounders and caveats:**
- The plan does not touch EIA-860m at all; no retirement/addition series exists in the catalogue. A gas *price* level says nothing about capacity *decisions*, which are planned years ahead and reported monthly with lag.
- The post-war drop is plausibly a US-specific story: record dry-gas and associated-gas output, storage above the 5-yr average, and spring/summer shoulder-season demand (the post window is dominated by Mar–Sep), while Hormuz disruption mainly affected LNG/oil abroad. Seasonality alone can generate a d of this size.
- Pre-window includes the Jan–Feb 2026 cold-snap spike (high pre sd), inflating the pre mean.
- Serial autocorrelation makes the Welch p grossly overstated; the permutation p (0.014) is the more honest figure.

**4) Follow-up:** Use PUDL EIA-923/930 monthly generation by fuel (freq=M): test whether gas share of US generation and battery discharge (EIA-930 BA-level) rose post-war vs the same months of 2025, with a regional split (ERCOT/CAISO vs MISO).
