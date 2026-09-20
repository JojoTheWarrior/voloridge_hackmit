# S-0009

| Field | Value |
|---|---|
| Mission id | `S-0009` |
| Folder | `20260920-213-weather-houston-radiation_x_finance-ng-f-log-return` |
| Indicators | `weather.houston.radiation` × `finance.NG=F.log_return` |
| n_obs | 388 |
| r | -0.0858512928724267 |
| Best lag | 0 (days) |
| perm_p | 0.5149700598802395 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.75, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.houston.radiation` (configured analysis window); `finance.NG=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.0858512928724267, n=388).

The best tested lag was 0 days with r=-0.0858512928724267.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short NG=F**, hold 1d
- Entry: weather.houston.radiation rolling_zscore_20d > 1 at close -> short NG=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=36 hit_rate=0.4166666666666667 avg_return=0.002510585189576432 excess=0.0028459952307269337 sharpe_like=0.3791859240341085 max_dd=-0.22759915368632677
- OOS (war period): n=13 hit=0.23076923076923078 avg=-0.004992282705638613
- Actionability: 1.75
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
