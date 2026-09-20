# R2-0151

| Field | Value |
|---|---|
| Mission id | `R2-0151` |
| Folder | `20260920-248-weather-houston-wind-max_x_finance-cf-abs-return` |
| Indicators | `weather.houston.wind_max` × `finance.CF.abs_return` |
| n_obs | 387 |
| r | 0.08092494966806915 |
| Best lag | 4 (days) |
| perm_p | 0.8223552894211577 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.28, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.houston.wind_max` (configured analysis window); `finance.CF.abs_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.08092494966806915, n=387).

The best tested lag was 4 days with r=0.10180242790577379.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 4d
- Entry: weather.houston.wind_max rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 4 trading days (no overlapping entries)
- n_trades=34 hit_rate=1.0 avg_return=0.07775800188148439 excess=0.0015303821937280165 sharpe_like=9.245518925052922 max_dd=0.0
- OOS (war period): n=15 hit=1.0 avg=0.09417415373382614
- Actionability: 7.28
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
