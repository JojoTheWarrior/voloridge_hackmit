# R2-0110

| Field | Value |
|---|---|
| Mission id | `R2-0110` |
| Folder | `20260920-220-airquality-dubai-cams-no2_x_finance-bz-f-log-return` |
| Indicators | `airquality.dubai.cams_no2` × `finance.BZ=F.log_return` |
| n_obs | 390 |
| r | 0.04162070117607827 |
| Best lag | -9 (days) |
| perm_p | 0.18363273453093812 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.41, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.dubai.cams_no2` (2025-03..2026-09 archive window); `finance.BZ=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.04162070117607827, n=390).

The best tested lag was -9 days with r=0.12484835268857121.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short BZ=F**, hold 1d
- Entry: airquality.dubai.cams_no2 rolling_zscore_20d > 1 at close -> short BZ=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=57 hit_rate=0.49122807017543857 avg_return=-0.0011079214027788357 excess=0.00040053376722899866 sharpe_like=-0.32888743759170386 max_dd=-0.22908829899327365
- OOS (war period): n=18 hit=0.2222222222222222 avg=-0.012592343221264075
- Actionability: 2.41
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
