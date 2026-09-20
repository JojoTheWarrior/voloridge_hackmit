# R2-0060

| Field | Value |
|---|---|
| Mission id | `R2-0060` |
| Folder | `20260920-173-airquality-dubai-cams-no2_x_finance-iag-l-log-return` |
| Indicators | `airquality.dubai.cams_no2` × `finance.IAG.L.log_return` |
| n_obs | 389 |
| r | -0.11311517435535264 |
| Best lag | 0 (days) |
| perm_p | 0.530938123752495 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.22, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.dubai.cams_no2` (2025-03..2026-09 archive window); `finance.IAG.L.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.11311517435535264, n=389).

The best tested lag was 0 days with r=-0.11311517435535265.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short IAG**, hold 1d
- Entry: airquality.dubai.cams_no2 rolling_zscore_20d > 1 at close -> short IAG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=55 hit_rate=0.45454545454545453 avg_return=0.0008973278618196473 excess=0.0019418177202408212 sharpe_like=0.25934938905619587 max_dd=-0.16497920274719236
- OOS (war period): n=18 hit=0.4444444444444444 avg=0.0015738241566451427
- Actionability: 5.22
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
