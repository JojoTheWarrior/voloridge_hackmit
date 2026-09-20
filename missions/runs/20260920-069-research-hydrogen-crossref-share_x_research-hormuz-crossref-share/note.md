# M20260920-bc169a

| Field | Value |
|---|---|
| Mission id | `M20260920-bc169a` |
| Folder | `20260920-069-research-hydrogen-crossref-share_x_research-hormuz-crossref-share` |
| Indicators | `research.hydrogen.crossref_share` × `research.hormuz.crossref_share` |
| n_obs | 81 |
| r | -0.037439470552035184 |
| Best lag | 0 (weeks) |
| perm_p | 0.6866267465069861 |
| Bonferroni | 0.6866267465069861 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 0.02, 'interestingness': 0.3, 'unexpectedness': 0.04, 'supported_prob': 0.07, 'judge_model': 'jev-1.13.0'} |
| Data sources | `research.hydrogen.crossref_share` (2025-03..current week); `research.hormuz.crossref_share` (2025-03..current week) |

**1. Verdict**

Supported as a null baseline: hydrogen vs. Hormuz Crossref shares show essentially no linear association (Pearson r ≈ −0.04, p ≈ 0.74).

---

**2. What the data shows**

- Sample: 81 weekly observations (2025-03-03 to 2026-09-14).  
- Contemporaneous correlation (lag 0):  
  - Pearson r = −0.037 (p = 0.74) → indistinguishable from zero.  
  - Spearman r = 0.20 (p ≈ 0.074) → weak, non-robust rank association.  
- Lag search: only lag 0 tested; best r = −0.037 at lag 0.  
- Permutation test: permuted p ≈ 0.69, consistent with noise.  
- No pre/post-war or event-study structure was specified or detected for this pair.

This behavior matches expectations for two largely unrelated research-topic share series, analogous to a static, non-war-sensitive Materials Project helium/noble-gas signal.

---

**3. Confounders and caveats**

- Both are **shares** within the Crossref corpus; co-movement could arise mechanically from changes in other topics, even if the two are unrelated.  
- Weekly aggregation may hide short bursts of topical coupling (e.g., multi-topic special issues).  
- The sample covers the war period, so any common shifts in overall publication volume or indexing practices could slightly distort shares, but none appear systematic here.  
- Spearman’s marginal p (~0.07) suggests occasional coincident ordering, but multiplicity and the null design make this unsurprising.

---

**4. Follow-up mission**

Use the same null framework on **Materials Project**: compare weekly counts of helium/noble-gas–containing entries to an unrelated, stable reference (e.g., total oxide entries), testing whether those truly behave as a time-invariant baseline across the war timeline.
