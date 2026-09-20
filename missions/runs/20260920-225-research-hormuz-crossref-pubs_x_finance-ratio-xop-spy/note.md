# R2-0117

| Field | Value |
|---|---|
| Mission id | `R2-0117` |
| Folder | `20260920-225-research-hormuz-crossref-pubs_x_finance-ratio-xop-spy` |
| Indicators | `research.hormuz.crossref_pubs` × `finance.ratio.xop_spy` |
| n_obs | 81 |
| r | 0.0648247574462034 |
| Best lag | 0 (weeks) |
| perm_p | 0.5828343313373253 |
| Bonferroni | 0.5828343313373253 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_pubs` (2025-03..current week); `finance.ratio.xop_spy` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.0648247574462034, n=81).

The best tested lag was 0 weeks with r=0.06482475744620339.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ratio:xop_spy**, hold 1d
- Entry: research.hormuz.crossref_pubs rolling_zscore_20d > 1 at close -> short ratio:xop_spy next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=7 hit_rate=0.2857142857142857 avg_return=-0.008059598006684638 excess=-0.0047839232504024685 sharpe_like=-1.7303080065010705 max_dd=-0.05212886623081059
- OOS (war period): n=2 hit=0.0 avg=-0.015713950597515902
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
