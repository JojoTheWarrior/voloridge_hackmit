# R2-0113

| Field | Value |
|---|---|
| Mission id | `R2-0113` |
| Folder | `20260920-222-airquality-bandar-abbas-cams-dust_x_finance-dht-log-return` |
| Indicators | `airquality.bandar_abbas.cams_dust` × `finance.DHT.log_return` |
| n_obs | 389 |
| r | -0.05792600296932186 |
| Best lag | 4 (days) |
| perm_p | 0.8542914171656687 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.41, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.bandar_abbas.cams_dust` (2025-03..2026-09 archive window); `finance.DHT.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.05792600296932186, n=389).

The best tested lag was 4 days with r=0.061491349382298076.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long DHT**, hold 4d
- Entry: airquality.bandar_abbas.cams_dust rolling_zscore_20d > 1 at close -> long DHT next session
- Exit: close after 4 trading days (no overlapping entries)
- n_trades=27 hit_rate=0.5185185185185185 avg_return=0.00110657318519387 excess=-0.008260303521729271 sharpe_like=0.17356524682144506 max_dd=-0.11719164261035919
- OOS (war period): n=10 hit=0.7 avg=-2.933642657900748e-05
- Actionability: 1.41
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
