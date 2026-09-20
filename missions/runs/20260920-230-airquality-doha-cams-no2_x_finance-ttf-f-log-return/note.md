# R2-0126

| Field | Value |
|---|---|
| Mission id | `R2-0126` |
| Folder | `20260920-230-airquality-doha-cams-no2_x_finance-ttf-f-log-return` |
| Indicators | `airquality.doha.cams_no2` × `finance.TTF=F.log_return` |
| n_obs | 390 |
| r | -0.06566589118462474 |
| Best lag | -5 (days) |
| perm_p | 0.7744510978043913 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.9, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.doha.cams_no2` (2025-03..2026-09 archive window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.06566589118462474, n=390).

The best tested lag was -5 days with r=-0.07743261857725262.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long TTF=F**, hold 1d
- Entry: airquality.doha.cams_no2 rolling_zscore_20d > 1 at close -> long TTF=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=56 hit_rate=0.5357142857142857 avg_return=0.00021359122078627526 excess=-0.002322800866017626 sharpe_like=0.05730152325965191 max_dd=-0.22158749008345202
- OOS (war period): n=20 hit=0.65 avg=0.007177873743889557
- Actionability: 3.9
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
