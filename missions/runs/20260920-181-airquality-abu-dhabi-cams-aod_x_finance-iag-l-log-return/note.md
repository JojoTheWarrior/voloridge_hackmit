# R2-0070

| Field | Value |
|---|---|
| Mission id | `R2-0070` |
| Folder | `20260920-181-airquality-abu-dhabi-cams-aod_x_finance-iag-l-log-return` |
| Indicators | `airquality.abu_dhabi.cams_aod` × `finance.IAG.L.log_return` |
| n_obs | 389 |
| r | -0.02871387443045978 |
| Best lag | -3 (days) |
| perm_p | 0.9840319361277445 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.4, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.abu_dhabi.cams_aod` (2025-03..2026-09 archive window); `finance.IAG.L.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.02871387443045978, n=389).

The best tested lag was -3 days with r=0.05716621315630582.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short IAG**, hold 1d
- Entry: airquality.abu_dhabi.cams_aod rolling_zscore_20d > 1 at close -> short IAG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=49 hit_rate=0.4897959183673469 avg_return=-0.0028683398892415273 excess=-0.0018238500308203536 sharpe_like=-0.8014125733344126 max_dd=-0.2456414756756109
- OOS (war period): n=22 hit=0.5454545454545454 avg=-0.004130226639099611
- Actionability: 0.4
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
