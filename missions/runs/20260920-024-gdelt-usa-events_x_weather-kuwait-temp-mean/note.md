# M20260920-8158a4

| Field | Value |
|---|---|
| Mission id | `M20260920-8158a4` |
| Folder | `20260920-024-gdelt-usa-events_x_weather-kuwait-temp-mean` |
| Indicators | `gdelt.usa.events` × `weather.kuwait.temp_mean` |
| n_obs | 564 |
| r | -0.1531018619478953 |
| Best lag | 0 (days) |
| perm_p | 0.0658682634730539 |
| Bonferroni | 0.0658682634730539 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 4.0, 'interestingness': 3.84, 'unexpectedness': 5.36, 'supported_prob': 0.04, 'judge_model': 'jev-1.13.0'} |
| Data sources | `gdelt.usa.events` (configured analysis window); `weather.kuwait.temp_mean` (configured analysis window) |

**1. Verdict**

Weakly supported: cooler days in Kuwait are modestly associated with fewer GDELT-coded U.S. “events” (Pearson r ≈ -0.15, Bonferroni-adjusted permutation p ≈ 0.066).

---

**2. What the data shows**

- Sample: **n = 564 daily observations** (2025‑03‑01 to 2026‑09‑15).  
- Contemporaneous correlation between daily GDELT U.S. event counts and Kuwait mean temperature:  
  - **Pearson r = -0.153 (p ≈ 0.00026)**  
  - **Spearman r = -0.141 (p ≈ 0.00080)**  
- Best lag: **0 days** (only contemporaneous lag tested).  
- **Permutation test p ≈ 0.066**; with 1 lag, Bonferroni p is the same (≈ 0.066), just above a 5% threshold.  
- No explicit pre‑/post‑war split or event‑study around key war dates was run in this mission.

The negative association is statistically detectable by classical tests but becomes only marginal under permutation-based inference, and the magnitude (|r| ≈ 0.15) is small.

---

**3. Confounders and caveats**

- Temperature is only a **rough, imperfect proxy** for sandstorms or low visibility; dust events can occur on hot days.  
- Strong **seasonality** in temperature and possibly in reporting intensity may induce spurious correlation.  
- GDELT “U.S. events” mix many event types and geographies; they are not specific to **airstrikes in Iraq/Kuwait**.  
- War timing, media attention cycles, and operational tempo are **common drivers** that could affect both variables.  
- No direct sandstorm or visibility metric was used, and only **same‑day** relationships were examined.

---

**4. Follow-up mission idea**

Replace temperature with a **direct dust/visibility index** (e.g., days with reported visibility below a threshold or dust-storm weather codes in Iraq and Kuwait) and correlate specifically with **GDELT airstrike/kinetic-event codes**, including a pre/post‑war event study and short lags (±3–5 days).
