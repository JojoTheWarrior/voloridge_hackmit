# R2-0072

| Field | Value |
|---|---|
| Mission id | `R2-0072` |
| Folder | `20260920-183-weather-bandar-abbas-temp-mean_x_finance-dal-log-return` |
| Indicators | `weather.bandar_abbas.temp_mean` × `finance.DAL.log_return` |
| n_obs | 387 |
| r | 0.029100513418808774 |
| Best lag | 5 (days) |
| perm_p | 0.8682634730538922 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.87, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.bandar_abbas.temp_mean` (configured analysis window); `finance.DAL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.029100513418808774, n=387).

The best tested lag was 5 days with r=0.03992743926154068.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long DAL**, hold 5d
- Entry: weather.bandar_abbas.temp_mean rolling_zscore_20d > 1 at close -> long DAL next session
- Exit: close after 5 trading days (no overlapping entries)
- n_trades=27 hit_rate=0.37037037037037035 avg_return=0.00118445235752751 excess=-0.007398262477543183 sharpe_like=0.08691941393974514 max_dd=-0.25325324440501173
- OOS (war period): n=10 hit=0.6 avg=0.029293976116125008
- Actionability: 1.87
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
