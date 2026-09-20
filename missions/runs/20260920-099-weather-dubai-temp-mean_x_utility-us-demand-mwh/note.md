# M20260920-35ee16

| Field | Value |
|---|---|
| Mission id | `M20260920-35ee16` |
| Folder | `20260920-099-weather-dubai-temp-mean_x_utility-us-demand-mwh` |
| Indicators | `weather.dubai.temp_mean` × `utility.us.demand_mwh` |
| n_obs | 555 |
| r | 0.48568094883380897 |
| Best lag | -1 (days) |
| perm_p | 0.013972055888223553 |
| Bonferroni | 0.8522954091816367 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 6.42, 'interestingness': 3.8, 'unexpectedness': 8.68, 'supported_prob': 0.15, 'judge_model': 'jev-1.13.0'} |
| Data sources | `weather.dubai.temp_mean` (configured analysis window); `utility.us.demand_mwh` (configured analysis window) |

**1. Verdict**

Weakly supported as a *null* control: despite a moderate raw correlation (|r|max ≈ 0.51), the multi‑lag test is not statistically significant after correction (Bonferroni p ≈ 0.85).

---

**2. What the data shows**

- Sample: n = 555 days (2025‑03‑01 to 2026‑09‑06).  
- Contemporaneous correlation (Dubai mean temperature vs. US total demand):  
  - Pearson r = 0.486 (p ≈ 3.4×10⁻³⁴)  
  - Spearman r = 0.540 (p ≈ 2.2×10⁻⁴³)  
- Best lagged correlation over ±30 days:  
  - Best r = 0.511 at lag −1 (Dubai leading US demand by 1 day).  
- Multiple‑testing adjustment over 61 lags:  
  - Permutation p = 0.014 (uncorrected)  
  - Bonferroni‑adjusted p ≈ 0.85 → not significant under a strict joint test.  
- No pre/post‑war or event‑study splits were applied here.

---

**3. Confounders and caveats**

- Strong shared seasonality: both Dubai temperature and US demand track the annual temperature cycle (AC demand in US summer vs. Dubai’s extreme summers), which can create a spurious positive correlation.  
- Common time trends and day‑of‑week patterns in US load are not removed.  
- Ignoring local US weather: the common driver is likely Northern Hemisphere seasonality, not any physical linkage between Dubai weather and US demand.  
- War‑period disruptions in energy markets might co‑move with both variables through global economic activity, further confounding raw correlations.

---

**4. Follow‑up mission idea**

Detrend and deseasonalize both series (and control for US weather) before re‑testing the Dubai–US demand relationship, to verify that any remaining correlation is consistent with pure noise for use as a robust null control.
