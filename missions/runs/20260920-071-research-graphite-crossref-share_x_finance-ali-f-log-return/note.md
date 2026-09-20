# M20260920-1fe137

| Field | Value |
|---|---|
| Mission id | `M20260920-1fe137` |
| Folder | `20260920-071-research-graphite-crossref-share_x_finance-ali-f-log-return` |
| Indicators | `research.graphite.crossref_share` × `finance.ALI=F.log_return` |
| n_obs | 81 |
| r | 0.15326688891063844 |
| Best lag | -1 (weeks) |
| perm_p | 0.6027944111776448 |
| Bonferroni | 1.0 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 0.1, 'interestingness': 1.5, 'unexpectedness': 0.86, 'supported_prob': 0.09, 'judge_model': 'jev-1.13.0'} |
| Data sources | `research.graphite.crossref_share` (2025-03..current week); `finance.ALI=F.log_return` (configured analysis window) |

**1. Verdict**

Weakly supported as a null control: no statistically robust relationship (|r| ≤ 0.20, permutation p = 0.60).

---

**2. What the data shows**

- Sample: n = 81 daily observations (2025-03-03 to 2026-09-14).  
- Contemporaneous association:  
  - Pearson r = 0.15 (p = 0.17)  
  - Spearman r = 0.18 (p = 0.11)  
  → Both small and not statistically significant.  
- Lag structure (lags in weeks, ±4 weeks tested):  
  - Best lag: –1 week (graphite share leading aluminum returns by 1 week)  
  - Best correlation: r = –0.20  
  - After multiple-testing adjustment: Bonferroni p = 1.0.  
- Permutation test over all alignments: p = 0.60 → correlations are well within what random reshuffling would generate.  
- No pre/post-war or event-study structure was specified or detected for this pair.

Overall, the graphite-related research-share series behaves like statistical noise with respect to aluminum futures returns, as hoped for a null.

---

**3. Confounders and caveats**

- The proxy is imperfect: graphite-related Crossref share is only loosely connected to aluminum or to Materials Project update intensity.  
- The sample is relatively short and spans an extreme period (2026 Iran war), which could create common macro shocks, even for unrelated series.  
- Seasonality in publication cycles and commodity trading could introduce low-level structure that happens to generate small, unstable correlations.

---

**4. Follow-up mission idea**

Test a **placebo pairing** using the same graphite research-share indicator against multiple unrelated commodity futures (e.g., corn, live cattle, silver) and summarize the empirical null distribution of max-|r| across lags, to benchmark how “surprising” any future materials–metal link really is.
