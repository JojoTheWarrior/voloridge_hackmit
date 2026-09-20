# S-0006

| Field | Value |
|---|---|
| Mission id | `S-0006` |
| Folder | `20260920-210-airquality-doha-cams-so2_x_finance-vg-log-return` |
| Indicators | `airquality.doha.cams_so2` × `finance.VG.log_return` |
| n_obs | 389 |
| r | 0.014368592800637865 |
| Best lag | 7 (days) |
| perm_p | 0.6147704590818364 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.doha.cams_so2` (2025-03..2026-09 archive window); `finance.VG.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.014368592800637865, n=389).

The best tested lag was 7 days with r=-0.11112600303766099.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long VG**, hold 7d
- Entry: airquality.doha.cams_so2 rolling_zscore_20d > 1 at close -> long VG next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=29 hit_rate=0.41379310344827586 avg_return=-0.004502492412245088 excess=-0.020636057926614434 sharpe_like=-0.1725370901798823 max_dd=-0.6564403403138694
- OOS (war period): n=11 hit=0.45454545454545453 avg=-0.005280255053605268
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
