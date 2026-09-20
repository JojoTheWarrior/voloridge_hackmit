# M20260920-3a5b5e

| Field | Value |
|---|---|
| Mission id | `M20260920-3a5b5e` |
| Folder | `20260920-108-research-graphite-crossref-pubs_x_finance-hg-f-close` |
| Indicators | `research.graphite.crossref_pubs` × `finance.HG=F.close` |
| n_obs | 81 |
| r | 0.10648435579986346 |
| Best lag | 0 (weeks) |
| perm_p | 0.4031936127744511 |
| Bonferroni | 0.4031936127744511 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 2.0, 'interestingness': 1.12, 'unexpectedness': 0.02, 'supported_prob': 0.07, 'judge_model': 'jev-1.13.0'} |
| Data sources | `research.graphite.crossref_pubs` (2025-03..current week); `finance.HG=F.close` (configured analysis window) |

**1. Verdict**

Inconclusive / consistent with no relationship: weekly Pearson r ≈ 0.11 (p ≈ 0.34) between graphite-related publications and copper returns.

---

**2. What the data shows**

- Sample: n = 81 weekly observations (2025-03-03 to 2026-09-14).  
- Correlation at 0 lag:  
  - Pearson r = 0.106 (p = 0.344)  
  - Spearman r = 0.077 (p = 0.496)  
- Lag search (0 weeks only by design):  
  - Best lag = 0 weeks, r = 0.106.  
- Permutation test: permuted p ≈ 0.40 (Bonferroni-adjusted p the same, since only one lag).  
- No pre/post-war or event-study structure was estimated for this control, so there is no detected shift around 2026 war milestones in this pair.

Overall, the data are fully compatible with random noise around zero correlation, as expected for a null control.

---

**3. Confounders and caveats**

- Publication counts are weekly and relatively low, potentially noisy and influenced by editorial cycles and academic calendars rather than markets.  
- Copper futures weekly percent changes are volatile and driven by many macro factors; over ~18 months, structural relationships are hard to detect.  
- Graphite-focused publications are only a proxy for broader materials-science intensity and may not track copper-relevant research.  
- Short window and small n limit power to detect any weak but real association.

---

**4. Follow-up mission idea**

Test the same publication series against **levels** of copper prices (and with multi-week lags), to confirm that the near-zero association is robust to alternative transformations and possible slow research-to-market dynamics.
