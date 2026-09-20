# R2-0061

| Field | Value |
|---|---|
| Mission id | `R2-0061` |
| Folder | `20260920-174-airquality-doha-cams-no2_x_finance-lha-de-log-return` |
| Indicators | `airquality.doha.cams_no2` × `finance.LHA.DE.log_return` |
| n_obs | 392 |
| r | 0.02276277364433812 |
| Best lag | 2 (days) |
| perm_p | 0.47105788423153694 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.11, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.doha.cams_no2` (2025-03..2026-09 archive window); `finance.LHA.DE.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.02276277364433812, n=392).

The best tested lag was 2 days with r=-0.10550150297560405.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short LHA**, hold 2d
- Entry: airquality.doha.cams_no2 rolling_zscore_20d > 1 at close -> short LHA next session
- Exit: close after 2 trading days (no overlapping entries)
- n_trades=46 hit_rate=0.5 avg_return=0.004250876891344346 excess=0.004719859434411356 sharpe_like=0.9141843001255089 max_dd=-0.1320383522778148
- OOS (war period): n=16 hit=0.5625 avg=0.0045971968028912305
- Actionability: 7.11
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
