# R2-0038

| Field | Value |
|---|---|
| Mission id | `R2-0038` |
| Folder | `20260920-158-weather-tokyo-temp-anomaly_x_finance-ttf-f-log-return` |
| Indicators | `weather.tokyo.temp_anomaly` × `finance.TTF=F.log_return` |
| n_obs | 388 |
| r | 0.02269613874808308 |
| Best lag | 10 (days) |
| perm_p | 0.02594810379241517 |
| Bonferroni | 0.5449101796407185 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.4, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.tokyo.temp_anomaly` (configured analysis window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.02269613874808308, n=388).

The best tested lag was 10 days with r=-0.14304906665747658.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short TTF=F**, hold 10d
- Entry: weather.tokyo.temp_anomaly rolling_zscore_20d > 1 at close -> short TTF=F next session
- Exit: close after 10 trading days (no overlapping entries)
- n_trades=20 hit_rate=0.65 avg_return=-0.028526456909056162 excess=-0.0025700961254051975 sharpe_like=-0.6517518502190993 max_dd=-0.8459643140907339
- OOS (war period): n=6 hit=0.3333333333333333 avg=-0.05369145571808217
- Actionability: 1.4
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
