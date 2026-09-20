# M20260920-1a83d1

| Field | Value |
|---|---|
| Mission id | `M20260920-1a83d1` |
| Folder | `20260920-008-weather-tehran-temp-mean_x_gdelt-irn-conflict-events` |
| Indicators | `weather.tehran.temp_mean` × `gdelt.irn.conflict_events` |
| n_obs | 564 |
| r | -0.18245504526481426 |
| Best lag | -1 (days) |
| perm_p | 0.6966067864271457 |
| Bonferroni | 1.0 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 0.08, 'interestingness': 2.4, 'unexpectedness': 3.96, 'supported_prob': 0.06, 'judge_model': 'jev-1.13.0'} |
| Data sources | `weather.tehran.temp_mean` (configured analysis window); `gdelt.irn.conflict_events` (configured analysis window) |

**1. Verdict**

Null-control verdict: **supported** – no robust relationship; strongest |r|≈0.19 at lag −1 with **permutation p≈0.70** (n=564).

---

**2. What the data shows**

- Sample: **564 daily observations** (2025‑03‑01 to 2026‑09‑15).  
- Contemporaneous Pearson correlation: **r = −0.18**, nominal p≈1.3×10⁻⁵, but Spearman **r ≈ 0.03**, p≈0.53.  
- Across lags −7…+7 days, correlations are small and stable: **best r = −0.19 at lag −1** (Tehran temperature leads conflict events by 1 day).  
- Multiple-testing adjustment: **Bonferroni p = 1.0** for the max-|r| across 15 lags.  
- Randomization check: **permutation p ≈ 0.70**, indicating the observed correlation pattern is fully consistent with chance given the temporal structure.  
- No pre/post-war split or event-study is computed here; the full window includes both pre‑ and post‑2026‑02‑28 war onset.

Overall, the weak, sign‑inconsistent, and non-robust correlations match the expectation of no systematic link.

---

**3. Confounders and caveats**

- **Seasonality in temperature** and any seasonal pattern in news coverage or conflict coding could induce small spurious correlations.  
- **Autocorrelation** in both series inflates nominal Pearson p‑values; hence the need for the permutation test.  
- GDELT counts reflect **coverage and coding intensity**, not ground‑truth conflict frequency.  
- Local temperature in Tehran may not reflect conditions in main conflict theaters elsewhere in Iran or the region.

---

**4. Follow‑up mission idea**

Test another placebo: **Tehran daily precipitation vs. Iran GDELT conflict-event counts**, including explicit seasonal controls (e.g., monthly dummies or detrending) to further validate the pipeline’s false‑positive rate.
