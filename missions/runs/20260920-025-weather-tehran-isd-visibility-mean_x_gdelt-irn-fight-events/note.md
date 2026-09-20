# M20260920-fe52b0

| Field | Value |
|---|---|
| Mission id | `M20260920-fe52b0` |
| Folder | `20260920-025-weather-tehran-isd-visibility-mean_x_gdelt-irn-fight-events` |
| Indicators | `weather.tehran.isd_visibility_mean` × `gdelt.irn.fight_events` |
| n_obs | 0 |
| r | None |
| Best lag | None (days) |
| perm_p | nan |
| Bonferroni | None |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 0.0, 'interestingness': 1.66, 'unexpectedness': 1.22, 'supported_prob': 0.02, 'judge_model': 'jev-1.13.0'} |
| Data sources | `weather.tehran.isd_visibility_mean` (2025-03..2025-08); `gdelt.irn.fight_events` (configured analysis window) |

**1. Verdict**

Inconclusive: no overlapping data between Tehran visibility and Iran fight events during the war window (n = 0), so the relationship cannot be evaluated.

---

**2. What the data shows**

- Overlap between `weather.tehran.isd_visibility_mean` and `gdelt.irn.fight_events` in the specified war window is **absent**:  
  - `n_obs = 0`, `coverage_start = null`, `coverage_end = null`.  
- Correlations cannot be computed:  
  - Pearson and Spearman coefficients are `null`; permutation p-value is `NaN`.  
- Lag analysis with lags −1, 0, +1 days yields all `NaN` correlations; no best lag is defined.  
- No pre/post-war comparison or event-study effects can be estimated (all `null`).

---

**3. Confounders and caveats**

- **Data availability / alignment** is the primary blocker: missing or non-overlapping series prevents any inference.
- Even if data were present, strike reporting intensity in GDELT depends on:
  - Media access, censorship, and internet connectivity.
  - Geographic mismatch (Tehran weather vs. strikes anywhere in Iran).
  - Overall war tempo and political incentives, which can dominate visibility effects.
- Strong **day-of-week and operational cycle** seasonality in conflict and in media output would need to be controlled.
- The war itself acts as a common driver of both military activity and reporting practices, complicating interpretation.

---

**4. Follow-up mission idea**

Re-run the analysis with a **country-level or regional satellite-derived cloud/visibility index** (e.g., over known strike regions in western/southern Iran) and **location-filtered GDELT events**, extending the window to pre-war and post-ceasefire to check whether low visibility systematically coincides with fewer reported strikes.
