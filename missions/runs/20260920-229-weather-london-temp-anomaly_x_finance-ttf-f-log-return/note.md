# R2-0125

| Field | Value |
|---|---|
| Mission id | `R2-0125` |
| Folder | `20260920-229-weather-london-temp-anomaly_x_finance-ttf-f-log-return` |
| Indicators | `weather.london.temp_anomaly` × `finance.TTF=F.log_return` |
| n_obs | 388 |
| r | 0.006624931180774231 |
| Best lag | 3 (days) |
| perm_p | 0.06986027944111776 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.49, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.london.temp_anomaly` (configured analysis window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.006624931180774231, n=388).

The best tested lag was 3 days with r=0.12314349764545938.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short TTF=F**, hold 3d
- Entry: weather.london.temp_anomaly rolling_zscore_20d > 1 at close -> short TTF=F next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=36 hit_rate=0.4166666666666667 avg_return=-0.008078259903902723 excess=-0.0006512774044819588 sharpe_like=-0.46932044459865513 max_dd=-0.5380678232873455
- OOS (war period): n=11 hit=0.5454545454545454 avg=0.005976054978401499
- Actionability: 2.49
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
