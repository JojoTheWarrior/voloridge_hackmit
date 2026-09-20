# S-0011

| Field | Value |
|---|---|
| Mission id | `S-0011` |
| Folder | `20260920-215-weather-oklahoma-city-precip_x_finance-zw-f-log-return` |
| Indicators | `weather.oklahoma_city.precip` × `finance.ZW=F.log_return` |
| n_obs | 387 |
| r | 0.04726857499735726 |
| Best lag | -4 (days) |
| perm_p | 0.20958083832335328 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.81, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.oklahoma_city.precip` (configured analysis window); `finance.ZW=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.04726857499735726, n=387).

The best tested lag was -4 days with r=-0.1114328018207931.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ZW=F**, hold 1d
- Entry: weather.oklahoma_city.precip rolling_zscore_20d > 1 at close -> short ZW=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=34 hit_rate=0.35294117647058826 avg_return=-0.001560844474232009 excess=-0.0006515060495265197 sharpe_like=-0.7635225202140851 max_dd=-0.11263967782777806
- OOS (war period): n=15 hit=0.5333333333333333 avg=0.003250502135745307
- Actionability: 2.81
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
