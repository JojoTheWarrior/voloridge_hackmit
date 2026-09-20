# R2-0123

| Field | Value |
|---|---|
| Mission id | `R2-0123` |
| Folder | `20260920-228-weather-rotterdam-wind-max_x_finance-ttf-f-log-return` |
| Indicators | `weather.rotterdam.wind_max` × `finance.TTF=F.log_return` |
| n_obs | 388 |
| r | -0.022754091585473594 |
| Best lag | -8 (days) |
| perm_p | 0.47105788423153694 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.67, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.rotterdam.wind_max` (configured analysis window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.022754091585473594, n=388).

The best tested lag was -8 days with r=0.10296871518777423.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long TTF=F**, hold 1d
- Entry: weather.rotterdam.wind_max rolling_zscore_20d > 1 at close -> long TTF=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=58 hit_rate=0.5172413793103449 avg_return=-0.0023258474612821863 excess=-0.004823366188809613 sharpe_like=-0.4922350947092965 max_dd=-0.2504986871682141
- OOS (war period): n=18 hit=0.5 avg=-0.0015158902817670923
- Actionability: 0.67
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
