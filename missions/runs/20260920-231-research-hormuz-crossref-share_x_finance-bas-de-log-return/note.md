# R2-0127

| Field | Value |
|---|---|
| Mission id | `R2-0127` |
| Folder | `20260920-231-research-hormuz-crossref-share_x_finance-bas-de-log-return` |
| Indicators | `research.hormuz.crossref_share` × `finance.BAS.DE.log_return` |
| n_obs | 81 |
| r | 0.056179548503531206 |
| Best lag | 1 (weeks) |
| perm_p | 0.2435129740518962 |
| Bonferroni | 0.7305389221556886 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_share` (2025-03..current week); `finance.BAS.DE.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.056179548503531206, n=81).

The best tested lag was 1 weeks with r=-0.22120043014290844.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short BAS**, hold 1d
- Entry: research.hormuz.crossref_share rolling_zscore_20d > 1 at close -> short BAS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=9 hit_rate=0.2222222222222222 avg_return=-0.005798293070757719 excess=-0.0035992434643418022 sharpe_like=-1.0356872386206835 max_dd=-0.05179191716705178
- OOS (war period): n=2 hit=0.0 avg=-0.0027338629011522952
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
