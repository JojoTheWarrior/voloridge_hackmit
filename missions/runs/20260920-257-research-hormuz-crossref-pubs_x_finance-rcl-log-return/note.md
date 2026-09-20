# R2-0165

| Field | Value |
|---|---|
| Mission id | `R2-0165` |
| Folder | `20260920-257-research-hormuz-crossref-pubs_x_finance-rcl-log-return` |
| Indicators | `research.hormuz.crossref_pubs` × `finance.RCL.log_return` |
| n_obs | 81 |
| r | -0.08919145642875266 |
| Best lag | 1 (weeks) |
| perm_p | 0.5049900199600799 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.05, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_pubs` (2025-03..current week); `finance.RCL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.08919145642875266, n=81).

The best tested lag was 1 weeks with r=-0.1595146157432384.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short RCL**, hold 1d
- Entry: research.hormuz.crossref_pubs rolling_zscore_20d > 1 at close -> short RCL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=7 hit_rate=0.42857142857142855 avg_return=-0.004909452453834133 excess=-0.007560128735029573 sharpe_like=-1.025227662156567 max_dd=-0.044028328569437614
- OOS (war period): n=2 hit=0.5 avg=0.002628825675863755
- Actionability: 1.05
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
