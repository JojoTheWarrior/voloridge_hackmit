# R2-0109

| Field | Value |
|---|---|
| Mission id | `R2-0109` |
| Folder | `20260920-219-weather-bandar-abbas-temp-anomaly_x_finance-spy-log-return` |
| Indicators | `weather.bandar_abbas.temp_anomaly` × `finance.SPY.log_return` |
| n_obs | 387 |
| r | -0.006983182743930255 |
| Best lag | -3 (days) |
| perm_p | 0.9620758483033932 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.05, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.bandar_abbas.temp_anomaly` (configured analysis window); `finance.SPY.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.006983182743930255, n=387).

The best tested lag was -3 days with r=0.04135483189578886.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long SPY**, hold 1d
- Entry: weather.bandar_abbas.temp_anomaly rolling_zscore_20d > 1 at close -> long SPY next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=55 hit_rate=0.45454545454545453 avg_return=-0.00026162632822531226 excess=-0.0010969061612549178 sharpe_like=-0.2612378534687764 max_dd=-0.07008903731655158
- OOS (war period): n=22 hit=0.5909090909090909 avg=0.0020386666066716697
- Actionability: 4.05
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
