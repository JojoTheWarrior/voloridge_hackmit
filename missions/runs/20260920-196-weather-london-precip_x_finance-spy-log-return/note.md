# R2-0093

| Field | Value |
|---|---|
| Mission id | `R2-0093` |
| Folder | `20260920-196-weather-london-precip_x_finance-spy-log-return` |
| Indicators | `weather.london.precip` × `finance.SPY.log_return` |
| n_obs | 387 |
| r | -0.014157975774566418 |
| Best lag | -1 (days) |
| perm_p | 0.6786427145708582 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.76, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.london.precip` (configured analysis window); `finance.SPY.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.014157975774566418, n=387).

The best tested lag was -1 days with r=-0.06556790558433574.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short SPY**, hold 1d
- Entry: weather.london.precip rolling_zscore_20d > 1 at close -> short SPY next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=47 hit_rate=0.425531914893617 avg_return=-0.0011995178090250856 excess=-0.0003642379759954802 sharpe_like=-0.9354333718577399 max_dd=-0.09394900280977758
- OOS (war period): n=15 hit=0.2 avg=-0.003239356277255963
- Actionability: 0.76
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
