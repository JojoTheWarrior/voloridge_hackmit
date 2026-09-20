# S-0005

| Field | Value |
|---|---|
| Mission id | `S-0005` |
| Folder | `20260920-209-airquality-basrah-cams-so2_x_finance-bz-f-log-return` |
| Indicators | `airquality.basrah.cams_so2` × `finance.BZ=F.log_return` |
| n_obs | 390 |
| r | -0.0373698713163291 |
| Best lag | 7 (days) |
| perm_p | 0.6367265469061876 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.14, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.basrah.cams_so2` (2025-03..2026-09 archive window); `finance.BZ=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.0373698713163291, n=390).

The best tested lag was 7 days with r=0.09694658340146502.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short BZ=F**, hold 7d
- Entry: airquality.basrah.cams_so2 rolling_zscore_20d > 1 at close -> short BZ=F next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=28 hit_rate=0.5 avg_return=-0.007510670555128968 excess=0.0033423528393785804 sharpe_like=-0.6079555226692677 max_dd=-0.3455740683345988
- OOS (war period): n=10 hit=0.3 avg=-0.02083967311811711
- Actionability: 2.14
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
