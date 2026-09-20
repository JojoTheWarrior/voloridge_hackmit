# M20260920-bea6ef

| Field | Value |
|---|---|
| Mission id | `M20260920-bea6ef` |
| Folder | `20260920-073-finance-gc-f-log-return_x_finance-bz-f-log-return` |
| Indicators | `finance.GC=F.log_return` × `finance.BZ=F.log_return` |
| n_obs | 391 |
| r | -0.1111940992511177 |
| Best lag | -4 (days) |
| perm_p | 0.21956087824351297 |
| Bonferroni | 1.0 |
| pre/post Δr | -0.43648911673246404 |
| Fisher p | 2.6184045082143695e-05 |
| Scores | {'validity': 2.3, 'interestingness': 4.46, 'unexpectedness': 5.1, 'supported_prob': 0.89, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.GC=F.log_return` (configured analysis window); `finance.BZ=F.log_return` (configured analysis window) |

**1. Verdict**

Weakly supported: the gold–Brent return correlation flips from +0.13 before the war to –0.31 afterward (Δr ≈ –0.44, Fisher z‑test p ≈ 2.6×10⁻⁵).

**2. What the data shows**

- Sample: n = 391 daily log returns (GC=F vs BZ=F), 2025‑03‑03 to 2026‑09‑18.  
- Full‑period correlation: Pearson r = –0.11 (p = 0.028); permutation p = 0.22 (not robust once we allow flexible lag structure / multiple testing).  
- Lag structure: best correlation at lag –4 (gold leading oil by 4 days) r = –0.12; Bonferroni‑adjusted p = 1.0 (no strong evidence at any specific lag).  
- Pre‑war window (up to 2026‑02‑27; n = 251): r = +0.13 (p ≈ 0.042), mild positive co‑movement.  
- War/post‑onset window (from 2026‑02‑28; n = 140): r = –0.31 (p ≈ 2.1×10⁻⁴), strong negative co‑movement—days when Brent rose tended to coincide with gold falling, and vice versa.  
- Change in correlation: Δr ≈ –0.44; Fisher z test for difference in correlations p ≈ 2.6×10⁻⁵, indicating a statistically significant regime shift in joint behavior.

**3. Confounders and caveats**

- Only ~6–7 months of “post” data; a few crisis episodes can dominate correlations.  
- Global macro shocks (rates, USD, equity volatility) could drive different responses in gold vs oil, independent of the Iran war.  
- Returns, not levels: this shows decoupling of daily moves, not that gold’s *price* necessarily trended down while oil rose.  
- Multiple comparisons across many WarSignal missions raise false‑positive risks.

**4. Follow‑up mission**

Test whether the gold–Brent correlation shift remains after controlling for USD index and VIX (e.g., partial correlations or regressions on common risk factors).
