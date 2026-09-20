# S-0013

| Field | Value |
|---|---|
| Mission id | `S-0013` |
| Folder | `20260920-217-airquality-houston-cams-so2_x_finance-hg-f-log-return` |
| Indicators | `airquality.houston.cams_so2` × `finance.HG=F.log_return` |
| n_obs | 390 |
| r | -0.07205287419942176 |
| Best lag | -9 (days) |
| perm_p | 0.7724550898203593 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.83, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.houston.cams_so2` (2025-03..2026-09 archive window); `finance.HG=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.07205287419942176, n=390).

The best tested lag was -9 days with r=-0.0797882587279522.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long HG=F**, hold 1d
- Entry: airquality.houston.cams_so2 rolling_zscore_20d > 1 at close -> long HG=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=45 hit_rate=0.5333333333333333 avg_return=-0.001595590201774444 excess=-0.0027709301168698415 sharpe_like=-0.2858071024246444 max_dd=-0.2463631667722861
- OOS (war period): n=18 hit=0.5 avg=0.0017753268557503994
- Actionability: 3.83
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
