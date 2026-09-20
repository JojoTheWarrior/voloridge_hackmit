# R2-0087

| Field | Value |
|---|---|
| Mission id | `R2-0087` |
| Folder | `20260920-192-research-hormuz-crossref-pubs_x_finance-inda-log-return` |
| Indicators | `research.hormuz.crossref_pubs` × `finance.INDA.log_return` |
| n_obs | 81 |
| r | -0.04552430128355965 |
| Best lag | 1 (weeks) |
| perm_p | 0.1996007984031936 |
| Bonferroni | 0.5988023952095809 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.79, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_pubs` (2025-03..current week); `finance.INDA.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.04552430128355965, n=81).

The best tested lag was 1 weeks with r=-0.209804408101603.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short INDA**, hold 1d
- Entry: research.hormuz.crossref_pubs rolling_zscore_20d > 1 at close -> short INDA next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=7 hit_rate=0.5714285714285714 avg_return=0.001024418359101577 excess=-0.0003050598150706452 sharpe_like=0.4785066049696387 max_dd=-0.011271317427436589
- OOS (war period): n=2 hit=0.5 avg=0.0007905094268505497
- Actionability: 2.79
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
