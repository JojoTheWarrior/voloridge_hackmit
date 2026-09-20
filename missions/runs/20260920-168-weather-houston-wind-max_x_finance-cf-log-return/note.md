# R2-0051

| Field | Value |
|---|---|
| Mission id | `R2-0051` |
| Folder | `20260920-168-weather-houston-wind-max_x_finance-cf-log-return` |
| Indicators | `weather.houston.wind_max` × `finance.CF.log_return` |
| n_obs | 387 |
| r | 0.03112391214133923 |
| Best lag | 10 (days) |
| perm_p | 0.10179640718562874 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.35, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.houston.wind_max` (configured analysis window); `finance.CF.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.03112391214133923, n=387).

The best tested lag was 10 days with r=0.14544263871156426.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 10d
- Entry: weather.houston.wind_max rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 10 trading days (no overlapping entries)
- n_trades=23 hit_rate=0.5652173913043478 avg_return=0.015581578664877272 excess=-0.001717889060444901 sharpe_like=1.0563496836060178 max_dd=-0.13957639607418848
- OOS (war period): n=9 hit=0.3333333333333333 avg=-0.0026875224295890903
- Actionability: 2.35
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
