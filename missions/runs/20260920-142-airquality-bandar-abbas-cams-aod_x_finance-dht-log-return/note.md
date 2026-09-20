# R2-0015

| Field | Value |
|---|---|
| Mission id | `R2-0015` |
| Folder | `20260920-142-airquality-bandar-abbas-cams-aod_x_finance-dht-log-return` |
| Indicators | `airquality.bandar_abbas.cams_aod` × `finance.DHT.log_return` |
| n_obs | 389 |
| r | -0.06324170293170595 |
| Best lag | 5 (days) |
| perm_p | 0.41317365269461076 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.59, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.bandar_abbas.cams_aod` (2025-03..2026-09 archive window); `finance.DHT.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.06324170293170595, n=389).

The best tested lag was 5 days with r=0.0807589239601519.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long DHT**, hold 5d
- Entry: airquality.bandar_abbas.cams_aod rolling_zscore_20d > 1 at close -> long DHT next session
- Exit: close after 5 trading days (no overlapping entries)
- n_trades=34 hit_rate=0.5588235294117647 avg_return=0.006839788388170738 excess=-0.004790476778171548 sharpe_like=1.0805709601549471 max_dd=-0.1236055196686704
- OOS (war period): n=12 hit=0.5833333333333334 avg=0.0025666000470417707
- Actionability: 2.59
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
