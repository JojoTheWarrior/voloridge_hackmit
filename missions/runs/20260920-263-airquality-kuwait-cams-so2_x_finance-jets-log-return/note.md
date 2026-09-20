# R2-0170

| Field | Value |
|---|---|
| Mission id | `R2-0170` |
| Folder | `20260920-263-airquality-kuwait-cams-so2_x_finance-jets-log-return` |
| Indicators | `airquality.kuwait.cams_so2` × `finance.JETS.log_return` |
| n_obs | 389 |
| r | 0.035582146202643716 |
| Best lag | -6 (days) |
| perm_p | 0.7764471057884231 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.6, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.kuwait.cams_so2` (2025-03..2026-09 archive window); `finance.JETS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.035582146202643716, n=389).

The best tested lag was -6 days with r=-0.07654014481927873.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short JETS**, hold 1d
- Entry: airquality.kuwait.cams_so2 rolling_zscore_20d > 1 at close -> short JETS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=49 hit_rate=0.5102040816326531 avg_return=-0.0053520241303136075 excess=-0.004437757179754442 sharpe_like=-1.1303091671506507 max_dd=-0.3455005276394001
- OOS (war period): n=18 hit=0.5555555555555556 avg=-0.002650041093314558
- Actionability: 0.6
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
