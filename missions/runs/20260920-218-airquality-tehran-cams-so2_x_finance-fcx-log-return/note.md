# S-0014

| Field | Value |
|---|---|
| Mission id | `S-0014` |
| Folder | `20260920-218-airquality-tehran-cams-so2_x_finance-fcx-log-return` |
| Indicators | `airquality.tehran.cams_so2` × `finance.FCX.log_return` |
| n_obs | 389 |
| r | 0.07811540015726048 |
| Best lag | 1 (days) |
| perm_p | 0.017964071856287425 |
| Bonferroni | 0.3772455089820359 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.82, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.tehran.cams_so2` (2025-03..2026-09 archive window); `finance.FCX.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.07811540015726048, n=389).

The best tested lag was 1 days with r=0.10341106485843732.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long FCX**, hold 1d
- Entry: airquality.tehran.cams_so2 rolling_zscore_20d > 1 at close -> long FCX next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=58 hit_rate=0.5172413793103449 avg_return=0.0009136901175955535 excess=-0.001510329128523245 sharpe_like=0.22758979536907092 max_dd=-0.1439787809248625
- OOS (war period): n=24 hit=0.4166666666666667 avg=-0.0027760303464999477
- Actionability: 1.82
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
