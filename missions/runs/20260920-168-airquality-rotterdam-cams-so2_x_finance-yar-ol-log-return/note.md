# R2-0052

| Field | Value |
|---|---|
| Mission id | `R2-0052` |
| Folder | `20260920-168-airquality-rotterdam-cams-so2_x_finance-yar-ol-log-return` |
| Indicators | `airquality.rotterdam.cams_so2` × `finance.YAR.OL.log_return` |
| n_obs | 386 |
| r | -0.010775429990820373 |
| Best lag | 2 (days) |
| perm_p | 0.2654690618762475 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.2, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.rotterdam.cams_so2` (2025-03..2026-09 archive window); `finance.YAR.OL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.010775429990820373, n=386).

The best tested lag was 2 days with r=0.11547829972805608.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long YAR**, hold 2d
- Entry: airquality.rotterdam.cams_so2 rolling_zscore_20d > 1 at close -> long YAR next session
- Exit: close after 2 trading days (no overlapping entries)
- n_trades=47 hit_rate=0.5319148936170213 avg_return=0.005477018097551424 excess=0.003558422768385929 sharpe_like=2.078515613658627 max_dd=-0.08842351801093862
- OOS (war period): n=19 hit=0.42105263157894735 avg=0.0017293978982366438
- Actionability: 8.2
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
