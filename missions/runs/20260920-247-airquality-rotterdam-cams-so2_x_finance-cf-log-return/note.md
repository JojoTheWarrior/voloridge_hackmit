# R2-0150

| Field | Value |
|---|---|
| Mission id | `R2-0150` |
| Folder | `20260920-247-airquality-rotterdam-cams-so2_x_finance-cf-log-return` |
| Indicators | `airquality.rotterdam.cams_so2` × `finance.CF.log_return` |
| n_obs | 389 |
| r | -0.04446881085386707 |
| Best lag | 6 (days) |
| perm_p | 0.654690618762475 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.52, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.rotterdam.cams_so2` (2025-03..2026-09 archive window); `finance.CF.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.04446881085386707, n=389).

The best tested lag was 6 days with r=-0.09484355520196178.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 6d
- Entry: airquality.rotterdam.cams_so2 rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=31 hit_rate=0.5806451612903226 avg_return=0.0072359736389083235 excess=-0.002843593993944956 sharpe_like=0.7478836469301084 max_dd=-0.1340908870412556
- OOS (war period): n=12 hit=0.5 avg=0.0029295133882601965
- Actionability: 2.52
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
