# S-0002

| Field | Value |
|---|---|
| Mission id | `S-0002` |
| Folder | `20260920-206-airquality-houston-cams-so2_x_finance-cf-log-return` |
| Indicators | `airquality.houston.cams_so2` × `finance.CF.log_return` |
| n_obs | 389 |
| r | -0.06122851001489595 |
| Best lag | 3 (days) |
| perm_p | 0.8203592814371258 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.6, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.houston.cams_so2` (2025-03..2026-09 archive window); `finance.CF.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.06122851001489595, n=389).

The best tested lag was 3 days with r=0.08258261393978039.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 3d
- Entry: airquality.houston.cams_so2 rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=35 hit_rate=0.6 avg_return=0.008848735099365571 excess=0.0038186028093897062 sharpe_like=1.9398820234714795 max_dd=-0.10144642948447746
- OOS (war period): n=13 hit=0.6153846153846154 avg=0.008967441558435839
- Actionability: 8.6
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
