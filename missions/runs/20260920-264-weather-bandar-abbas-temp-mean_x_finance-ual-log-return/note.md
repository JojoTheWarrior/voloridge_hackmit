# R2-0172

| Field | Value |
|---|---|
| Mission id | `R2-0172` |
| Folder | `20260920-264-weather-bandar-abbas-temp-mean_x_finance-ual-log-return` |
| Indicators | `weather.bandar_abbas.temp_mean` × `finance.UAL.log_return` |
| n_obs | 387 |
| r | 0.03932026813905751 |
| Best lag | -10 (days) |
| perm_p | 0.5229540918163673 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.91, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.bandar_abbas.temp_mean` (configured analysis window); `finance.UAL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.03932026813905751, n=387).

The best tested lag was -10 days with r=0.05517367366642562.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long UAL**, hold 1d
- Entry: weather.bandar_abbas.temp_mean rolling_zscore_20d > 1 at close -> long UAL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=59 hit_rate=0.423728813559322 avg_return=0.001664306635477417 excess=0.00025558490920176975 sharpe_like=0.25244350082933115 max_dd=-0.1664765942991011
- OOS (war period): n=24 hit=0.4166666666666667 avg=0.001354191061774294
- Actionability: 4.91
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
