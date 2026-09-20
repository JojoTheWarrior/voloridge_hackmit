# R2-0128

| Field | Value |
|---|---|
| Mission id | `R2-0128` |
| Folder | `20260920-230-airquality-doha-cams-so2_x_finance-ttf-f-log-return` |
| Indicators | `airquality.doha.cams_so2` × `finance.TTF=F.log_return` |
| n_obs | 390 |
| r | -0.016625913658061563 |
| Best lag | 6 (days) |
| perm_p | 0.9860279441117764 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.6, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.doha.cams_so2` (2025-03..2026-09 archive window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.016625913658061563, n=390).

The best tested lag was 6 days with r=0.05895833068083843.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long TTF=F**, hold 6d
- Entry: airquality.doha.cams_so2 rolling_zscore_20d > 1 at close -> long TTF=F next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=31 hit_rate=0.5483870967741935 avg_return=0.03466622371394325 excess=0.0189984486573023 sharpe_like=1.3552962813532308 max_dd=-0.18763949308130723
- OOS (war period): n=13 hit=0.6153846153846154 avg=0.020514978184672048
- Actionability: 3.6
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
