# S-0003

| Field | Value |
|---|---|
| Mission id | `S-0003` |
| Folder | `20260920-207-airquality-houston-cams-co_x_finance-lng-log-return` |
| Indicators | `airquality.houston.cams_co` × `finance.LNG.log_return` |
| n_obs | 389 |
| r | -0.019583225691778134 |
| Best lag | -4 (days) |
| perm_p | 0.5808383233532934 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.21, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.houston.cams_co` (2025-03..2026-09 archive window); `finance.LNG.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.019583225691778134, n=389).

The best tested lag was -4 days with r=-0.09223159744410364.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long LNG**, hold 1d
- Entry: airquality.houston.cams_co rolling_zscore_20d > 1 at close -> long LNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=48 hit_rate=0.5416666666666666 avg_return=0.0010969734423723805 excess=0.0003333364830024147 sharpe_like=0.4352585754287959 max_dd=-0.05832397663217215
- OOS (war period): n=17 hit=0.5294117647058824 avg=-0.00014673344325205292
- Actionability: 4.21
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
