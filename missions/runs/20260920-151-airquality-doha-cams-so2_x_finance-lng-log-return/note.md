# R2-0029

| Field | Value |
|---|---|
| Mission id | `R2-0029` |
| Folder | `20260920-151-airquality-doha-cams-so2_x_finance-lng-log-return` |
| Indicators | `airquality.doha.cams_so2` × `finance.LNG.log_return` |
| n_obs | 389 |
| r | 0.06516519826114103 |
| Best lag | -1 (days) |
| perm_p | 0.626746506986028 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.61, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.doha.cams_so2` (2025-03..2026-09 archive window); `finance.LNG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.06516519826114103, n=389).

The best tested lag was -1 days with r=0.09110315178231489.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long LNG**, hold 1d
- Entry: airquality.doha.cams_so2 rolling_zscore_20d > 1 at close -> long LNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=47 hit_rate=0.5106382978723404 avg_return=-0.00022401425292017704 excess=-0.000987651212290143 sharpe_like=-0.09427263859050193 max_dd=-0.11623675103834374
- OOS (war period): n=21 hit=0.5238095238095238 avg=0.0018125796981697303
- Actionability: 4.61
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
