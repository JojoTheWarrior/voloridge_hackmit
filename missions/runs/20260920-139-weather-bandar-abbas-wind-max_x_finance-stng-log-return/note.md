# R2-0010

| Field | Value |
|---|---|
| Mission id | `R2-0010` |
| Folder | `20260920-139-weather-bandar-abbas-wind-max_x_finance-stng-log-return` |
| Indicators | `weather.bandar_abbas.wind_max` × `finance.STNG.log_return` |
| n_obs | 387 |
| r | 0.006285517430793598 |
| Best lag | -1 (days) |
| perm_p | 0.9101796407185628 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.68, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.bandar_abbas.wind_max` (configured analysis window); `finance.STNG.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.006285517430793598, n=387).

The best tested lag was -1 days with r=-0.05333981214617905.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long STNG**, hold 1d
- Entry: weather.bandar_abbas.wind_max rolling_zscore_20d > 1 at close -> long STNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=53 hit_rate=0.5849056603773585 avg_return=0.0014326223020999988 excess=-0.0009784509378484131 sharpe_like=0.4897250519114952 max_dd=-0.10493298077531021
- OOS (war period): n=19 hit=0.5263157894736842 avg=0.00018474231725098078
- Actionability: 2.68
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
