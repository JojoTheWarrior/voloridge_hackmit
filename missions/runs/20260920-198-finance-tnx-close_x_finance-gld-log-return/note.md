# R2-0097

| Field | Value |
|---|---|
| Mission id | `R2-0097` |
| Folder | `20260920-198-finance-tnx-close_x_finance-gld-log-return` |
| Indicators | `finance.^TNX.close` × `finance.GLD.log_return` |
| n_obs | 389 |
| r | -0.16736457698644971 |
| Best lag | 0 (days) |
| perm_p | 0.043912175648702596 |
| Bonferroni | 0.9221556886227545 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.39, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.^TNX.close` (configured analysis window); `finance.GLD.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.16736457698644971, n=389).

The best tested lag was 0 days with r=-0.16736457698644966.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short GLD**, hold 1d
- Entry: finance.^TNX.close rolling_zscore_20d > 1 at close -> short GLD next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=0.3888888888888889 avg_return=-0.0025868286822986436 excess=-0.0014666819526206205 sharpe_like=-1.2069567962773293 max_dd=-0.13252317709582373
- OOS (war period): n=23 hit=0.391304347826087 avg=-0.0005812580568355821
- Actionability: 0.39
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
