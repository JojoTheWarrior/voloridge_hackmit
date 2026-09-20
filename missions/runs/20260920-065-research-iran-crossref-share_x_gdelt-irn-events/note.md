# M20260920-562e15

| Field | Value |
|---|---|
| Mission id | `M20260920-562e15` |
| Folder | `20260920-065-research-iran-crossref-share_x_gdelt-irn-events` |
| Indicators | `research.iran.crossref_share` × `gdelt.irn.events` |
| n_obs | 81 |
| r | -0.21709450451384973 |
| Best lag | 0 (weeks) |
| perm_p | 0.27944111776447106 |
| Bonferroni | 0.27944111776447106 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 2.02, 'interestingness': 3.68, 'unexpectedness': 3.36, 'supported_prob': 0.05, 'judge_model': 'jev-1.13.0'} |
| Data sources | `research.iran.crossref_share` (2025-03..current week); `gdelt.irn.events` (configured analysis window) |

**1. Verdict**

Inconclusive: the inferred Iran-related publication share dips slightly around war events (mean change ≈ -0.53 units), but effects are small and statistically weak (event-study p ≈ 0.47; overall permuted p ≈ 0.28).

---

**2. What the data shows**

- Sample: 81 daily observations (2025‑03‑03 to 2026‑09‑14).  
- Contemporaneous association between Iran’s Crossref-share proxy and Iran-related GDELT events:
  - Pearson r ≈ -0.22 (p ≈ 0.052, marginal, n=81).  
  - Spearman r ≈ 0.03 (p ≈ 0.77).  
- Lag search (0 days only): best r = -0.22 at lag 0.  
- Permutation test (war events as shocks): p ≈ 0.28 (Bonferroni same, 1 lag).  
- Event study around 20 war/news dates:
  - Research proxy: mean pre ≈ 10.80, mean post ≈ 10.08, mean change ≈ -0.53, t ≈ -0.74, p ≈ 0.47.  
  - News intensity (GDELT IRN events) jumps strongly (mean change ≈ +2273, p ≈ 0.08), confirming the war-signal, not the publication effect.

Overall: only a mild, noisy, short-run dip in the Iran-related publication share, not distinguishable from random variation.

---

**3. Confounders and caveats**

- The “Iran publication share” is a heuristic Crossref/OpenAlex text-based proxy, not authoritative affiliation metadata.  
- Publications have long lags from research to indexing; a few war months may barely affect daily counts.  
- Seasonality and secular growth in global output could move the denominator, altering “share” without real Iranian decline.  
- GDELT spikes during war may co-move with global attention or data quality, not with Iranian research activity.

---

**4. Follow-up mission idea**

Test monthly Iran-affiliated article *acceptance* or indexing counts (with explicit affiliation IDs) vs. pre‑war trend, controlling for global output and known journal production cycles.
