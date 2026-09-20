# R2-0112

| Field | Value |
|---|---|
| Mission id | `R2-0112` |
| Folder | `20260920-221-weather-bandar-abbas-wind-max_x_finance-stng-log-return` |
| Indicators | `weather.bandar_abbas.wind_max` × `finance.STNG.log_return` |
| n_obs | 387 |
| r | 0.006285517430793598 |
| Best lag | 8 (days) |
| perm_p | 0.5848303393213573 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.bandar_abbas.wind_max` (configured analysis window); `finance.STNG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.006285517430793598, n=387).

The best tested lag was 8 days with r=-0.08123519829455852.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short STNG**, hold 8d
- Entry: weather.bandar_abbas.wind_max rolling_zscore_20d > 1 at close -> short STNG next session
- Exit: close after 8 trading days (no overlapping entries)
- n_trades=23 hit_rate=0.34782608695652173 avg_return=-0.027031293959015674 excess=-0.00791201535744487 sharpe_like=-2.253310991417577 max_dd=-0.4836465747770753
- OOS (war period): n=8 hit=0.375 avg=-0.03571862924585455
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
