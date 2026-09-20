# S-0001

| Field | Value |
|---|---|
| Mission id | `S-0001` |
| Folder | `20260920-205-airquality-houston-cams-no2_x_finance-ng-f-log-return` |
| Indicators | `airquality.houston.cams_no2` × `finance.NG=F.log_return` |
| n_obs | 390 |
| r | -0.185823149382957 |
| Best lag | 0 (days) |
| perm_p | 0.01996007984031936 |
| Bonferroni | 0.41916167664670656 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.05, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.houston.cams_no2` (2025-03..2026-09 archive window); `finance.NG=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.185823149382957, n=390).

The best tested lag was 0 days with r=-0.18582314938295713.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long NG=F**, hold 1d
- Entry: airquality.houston.cams_no2 rolling_zscore_20d > 1 at close -> long NG=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=55 hit_rate=0.45454545454545453 avg_return=-0.009088210307298923 excess=-0.009440711140485687 sharpe_like=-0.9241393830985244 max_dd=-0.6014256923741068
- OOS (war period): n=18 hit=0.3333333333333333 avg=-0.010048091661952177
- Actionability: 0.05
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
