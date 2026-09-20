# R2-0168

| Field | Value |
|---|---|
| Mission id | `R2-0168` |
| Folder | `20260920-259-airquality-dubai-cams-dust_x_finance-iag-l-log-return` |
| Indicators | `airquality.dubai.cams_dust` × `finance.IAG.L.log_return` |
| n_obs | 389 |
| r | -0.013199857231455489 |
| Best lag | -8 (days) |
| perm_p | 0.5229540918163673 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.32, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.dubai.cams_dust` (2025-03..2026-09 archive window); `finance.IAG.L.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.013199857231455489, n=389).

The best tested lag was -8 days with r=0.10213875780479785.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short IAG**, hold 1d
- Entry: airquality.dubai.cams_dust rolling_zscore_20d > 1 at close -> short IAG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=46 hit_rate=0.5434782608695652 avg_return=0.0017858988648049579 excess=0.0028303887232261314 sharpe_like=0.57783572453152 max_dd=-0.1369507263191322
- OOS (war period): n=16 hit=0.75 avg=0.007080272751062752
- Actionability: 7.32
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
