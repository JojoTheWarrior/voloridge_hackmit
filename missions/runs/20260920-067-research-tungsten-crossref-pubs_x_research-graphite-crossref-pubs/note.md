# M20260920-594bec

| Field | Value |
|---|---|
| Mission id | `M20260920-594bec` |
| Folder | `20260920-067-research-tungsten-crossref-pubs_x_research-graphite-crossref-pubs` |
| Indicators | `research.tungsten.crossref_pubs` × `research.graphite.crossref_pubs` |
| n_obs | 52 |
| r | 0.21982105447595032 |
| Best lag | 0 (weeks) |
| perm_p | 0.11776447105788423 |
| Bonferroni | 0.11776447105788423 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 4.0, 'interestingness': 1.38, 'unexpectedness': 0.84, 'supported_prob': 0.05, 'judge_model': 'jev-1.13.0'} |
| Data sources | `research.tungsten.crossref_pubs` (2025-03..current week); `research.graphite.crossref_pubs` (2025-03..current week) |

**1. Verdict**

Inconclusive: tungsten vs. graphite weekly publication counts pre‑war are only weakly related (Pearson r ≈ 0.22, p ≈ 0.12; permutation p ≈ 0.12).

---

**2. What the data shows**

- Sample: 52 weekly observations (2025‑03‑03 to 2026‑02‑23, pre‑war window only).  
- Levels of Crossref tungsten vs. graphite publications:  
  - Pearson r = 0.22 (p = 0.12)  
  - Spearman r = 0.26 (p = 0.064)  
- No lag structure: best lag = 0 weeks; r at that lag = 0.22.  
- Permutation test for association: p ≈ 0.118 (Bonferroni‑adjusted p is the same, since only 1 lag).  
- No pre/post‑war comparisons or event‑study effects were estimated by design (null‑control in pre‑war window only).

Statistically, we can’t reject the null of “no systematic difference/relationship” between tungsten and graphite publication levels in this period, which is consistent with this being a null control, but the evidence is weak rather than strongly confirming equal behavior.

---

**3. Confounders and caveats**

- Publications respond slowly to economic or supply shocks; 2025 activity may reflect earlier research agendas.  
- Discipline‑specific trends: tungsten vs. graphite may live in different subfields with different funding and seasonality.  
- Weekly counts are noisy; 52 weeks is a short span for structural inferences.  
- Crossref indexing practices or conference cycles could differ by keyword in ways unrelated to materials markets.

---

**4. Follow‑up mission**

Compare 2025 vs. 2026 tungsten publication intensity to graphite using a differences‑in‑differences design around the 2026‑02‑28 war start, testing for a relative post‑war shift in tungsten research focus.
