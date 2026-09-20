# S-0010

| Field | Value |
|---|---|
| Mission id | `S-0010` |
| Folder | `20260920-214-weather-houston-radiation_x_finance-xlu-log-return` |
| Indicators | `weather.houston.radiation` × `finance.XLU.log_return` |
| n_obs | 387 |
| r | -0.034121727403109384 |
| Best lag | 9 (days) |
| perm_p | 0.9201596806387226 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.94, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.houston.radiation` (configured analysis window); `finance.XLU.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.034121727403109384, n=387).

The best tested lag was 9 days with r=-0.05801857122631597.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long XLU**, hold 9d
- Entry: weather.houston.radiation rolling_zscore_20d > 1 at close -> long XLU next session
- Exit: close after 9 trading days (no overlapping entries)
- n_trades=19 hit_rate=0.5789473684210527 avg_return=0.0017661425428615771 excess=-0.00024627384293147135 sharpe_like=0.4246200650870146 max_dd=-0.0920651473592351
- OOS (war period): n=8 hit=0.25 avg=-0.011886956152983727
- Actionability: 1.94
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
