# R2-0053

| Field | Value |
|---|---|
| Mission id | `R2-0053` |
| Folder | `20260920-169-airquality-doha-cams-no2_x_finance-ntr-log-return` |
| Indicators | `airquality.doha.cams_no2` × `finance.NTR.log_return` |
| n_obs | 389 |
| r | 0.07241226328408565 |
| Best lag | 10 (days) |
| perm_p | 0.6487025948103793 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.78, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.doha.cams_no2` (2025-03..2026-09 archive window); `finance.NTR.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.07241226328408565, n=389).

The best tested lag was 10 days with r=0.09200658671170008.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long NTR**, hold 10d
- Entry: airquality.doha.cams_no2 rolling_zscore_20d > 1 at close -> long NTR next session
- Exit: close after 10 trading days (no overlapping entries)
- n_trades=23 hit_rate=0.4782608695652174 avg_return=-0.0005333799706536184 excess=-0.01337548684324843 sharpe_like=-0.05239120691484196 max_dd=-0.2427139513712615
- OOS (war period): n=7 hit=0.42857142857142855 avg=0.012287152444748397
- Actionability: 2.78
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
