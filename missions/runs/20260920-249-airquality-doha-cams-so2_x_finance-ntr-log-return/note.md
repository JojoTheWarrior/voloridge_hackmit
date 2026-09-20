# R2-0152

| Field | Value |
|---|---|
| Mission id | `R2-0152` |
| Folder | `20260920-249-airquality-doha-cams-so2_x_finance-ntr-log-return` |
| Indicators | `airquality.doha.cams_so2` × `finance.NTR.log_return` |
| n_obs | 389 |
| r | 0.04751208696891651 |
| Best lag | 9 (days) |
| perm_p | 0.31137724550898205 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.79, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.doha.cams_so2` (2025-03..2026-09 archive window); `finance.NTR.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.04751208696891651, n=389).

The best tested lag was 9 days with r=0.11913291996656111.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long NTR**, hold 9d
- Entry: airquality.doha.cams_so2 rolling_zscore_20d > 1 at close -> long NTR next session
- Exit: close after 9 trading days (no overlapping entries)
- n_trades=25 hit_rate=0.52 avg_return=0.009993339703637813 excess=-0.0015874458261747309 sharpe_like=0.8071074019105562 max_dd=-0.22192058081495125
- OOS (war period): n=10 hit=0.4 avg=0.0042357298452398995
- Actionability: 3.79
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
