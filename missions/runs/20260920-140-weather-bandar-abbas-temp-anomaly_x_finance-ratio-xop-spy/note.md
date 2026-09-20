# R2-0012

| Field | Value |
|---|---|
| Mission id | `R2-0012` |
| Folder | `20260920-140-weather-bandar-abbas-temp-anomaly_x_finance-ratio-xop-spy` |
| Indicators | `weather.bandar_abbas.temp_anomaly` × `finance.ratio.xop_spy` |
| n_obs | 386 |
| r | -0.004907020405752497 |
| Best lag | 10 (days) |
| perm_p | 0.6027944111776448 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.37, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.bandar_abbas.temp_anomaly` (configured analysis window); `finance.ratio.xop_spy` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.004907020405752497, n=386).

The best tested lag was 10 days with r=-0.08471342000948777.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ratio:xop_spy**, hold 10d
- Entry: weather.bandar_abbas.temp_anomaly rolling_zscore_20d > 1 at close -> long ratio:xop_spy next session
- Exit: close after 10 trading days (no overlapping entries)
- n_trades=21 hit_rate=0.5714285714285714 avg_return=0.012096082585659227 excess=0.007052722063940938 sharpe_like=1.0856909697148256 max_dd=-0.15109948045446753
- OOS (war period): n=6 hit=0.5 avg=0.010903112368297108
- Actionability: 6.37
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
