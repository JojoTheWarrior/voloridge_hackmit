# M20260920-5915ce

| Field | Value |
|---|---|
| Mission id | `M20260920-5915ce` |
| Folder | `20260920-107-finance-fred-dcoilbrenteu_x_utility-us-demand-peak-mwh` |
| Indicators | `finance.fred.DCOILBRENTEU` × `utility.us.demand_peak_mwh` |
| n_obs | 394 |
| r | -0.01585716549223919 |
| Best lag | 28 (days) |
| perm_p | 0.716566866267465 |
| Bonferroni | 1.0 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 0.06, 'interestingness': 2.1, 'unexpectedness': 0.18, 'supported_prob': 0.06, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.fred.DCOILBRENTEU` (configured analysis window); `utility.us.demand_peak_mwh` (configured analysis window) |

**1. Verdict**

Supported: no meaningful relationship detected (|r| ≤ 0.02 at lag 0; best |r|≈0.09 with p≈0.72 after permutation).

---

**2. What the data shows**

- Sample: n = 394 daily observations (2025-03-04 to 2026-09-04).  
- Contemporaneous link (Brent % change vs US peak demand level):  
  - Pearson r = -0.016, p = 0.75  
  - Spearman r = -0.034, p = 0.49  
- Lag search over ±30 days (61 lags):  
  - Maximum absolute correlation: r = -0.094 at lag +28 days (oil moves first).  
  - This is still very small; Bonferroni-adjusted p = 1.0.  
- Permutation test over the full correlation structure: permuted p = 0.72.  
- No pre/post-war or event-study structure was specified; results are for the full window including the war and shipping disruptions.

Overall, correlations are near zero across all lags and not statistically distinguishable from randomness.

---

**3. Confounders and caveats**

- US peak electricity demand is heavily driven by **weather and seasonality** (temperature, humidity) rather than commodity prices; we did not explicitly de-seasonalize demand.  
- Brent is expressed as **daily percent changes**, while demand is in **levels**; alternative scaling (e.g., anomalies) might yield slightly different noise patterns but is unlikely to create a strong link.  
- The 2026 Iran war and Hormuz closure may influence both series indirectly (macroeconomic conditions, fuel switching), but the daily, short-run mapping remains negligible here.  
- Multiple testing across lags raises the risk of spurious small correlations, mitigated (and essentially nullified) by the Bonferroni and permutation results.

---

**4. Follow-up mission**

Test whether **US natural-gas spot prices or power-sector natural-gas burn** show stronger short-run co-movement with Brent during war-related oil shocks than in pre-war months.
