# R2-0031

| Field | Value |
|---|---|
| Mission id | `R2-0031` |
| Folder | `20260920-154-research-hormuz-crossref-pubs_x_finance-lng-log-return` |
| Indicators | `research.hormuz.crossref_pubs` × `finance.LNG.log_return` |
| n_obs | 81 |
| r | 0.1303228378227526 |
| Best lag | 0 (weeks) |
| perm_p | 0.45109780439121755 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.98, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_pubs` (2025-03..current week); `finance.LNG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.1303228378227526, n=81).

The best tested lag was 0 weeks with r=0.1303228378227526.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long LNG**, hold 1d
- Entry: research.hormuz.crossref_pubs rolling_zscore_20d > 1 at close -> long LNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=7 hit_rate=0.5714285714285714 avg_return=0.00468734956547856 excess=0.003931737056259468 sharpe_like=0.7551024252347781 max_dd=-0.016507003243209306
- OOS (war period): n=2 hit=1.0 avg=0.022020839508737344
- Actionability: 4.98
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
