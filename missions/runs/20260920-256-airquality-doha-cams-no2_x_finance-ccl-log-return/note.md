# R2-0161

| Field | Value |
|---|---|
| Mission id | `R2-0161` |
| Folder | `20260920-256-airquality-doha-cams-no2_x_finance-ccl-log-return` |
| Indicators | `airquality.doha.cams_no2` × `finance.CCL.log_return` |
| n_obs | 389 |
| r | -0.06998705521118977 |
| Best lag | -8 (days) |
| perm_p | 0.7664670658682635 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.5, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.doha.cams_no2` (2025-03..2026-09 archive window); `finance.CCL.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.06998705521118977, n=389).

The best tested lag was -8 days with r=0.09186855422053554.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short CCL**, hold 1d
- Entry: airquality.doha.cams_no2 rolling_zscore_20d > 1 at close -> short CCL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=56 hit_rate=0.5 avg_return=-0.0026676616847853113 excess=-0.0018463441839276186 sharpe_like=-0.6935527913179305 max_dd=-0.35426608501734347
- OOS (war period): n=20 hit=0.7 avg=0.013176211908756601
- Actionability: 3.5
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
