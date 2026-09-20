# R2-0135

| Field | Value |
|---|---|
| Mission id | `R2-0135` |
| Folder | `20260920-236-weather-tokyo-temp-anomaly_x_finance-ratio-ttf-henryhub` |
| Indicators | `weather.tokyo.temp_anomaly` × `finance.ratio.ttf_henryhub` |
| n_obs | 387 |
| r | -0.00718778873194437 |
| Best lag | 7 (days) |
| perm_p | 0.3033932135728543 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.98, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.tokyo.temp_anomaly` (configured analysis window); `finance.ratio.ttf_henryhub` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.00718778873194437, n=387).

The best tested lag was 7 days with r=-0.08926018984955815.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ratio:ttf_henryhub**, hold 7d
- Entry: weather.tokyo.temp_anomaly rolling_zscore_20d > 1 at close -> long ratio:ttf_henryhub next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=25 hit_rate=0.52 avg_return=0.029627818835235402 excess=-0.001814153670366754 sharpe_like=1.093029232296893 max_dd=-0.19759208004947626
- OOS (war period): n=10 hit=0.4 avg=0.004927495232584433
- Actionability: 0.98
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
