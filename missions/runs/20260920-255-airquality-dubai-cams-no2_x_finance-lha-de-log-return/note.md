# R2-0160

| Field | Value |
|---|---|
| Mission id | `R2-0160` |
| Folder | `20260920-255-airquality-dubai-cams-no2_x_finance-lha-de-log-return` |
| Indicators | `airquality.dubai.cams_no2` × `finance.LHA.DE.log_return` |
| n_obs | 392 |
| r | -0.09381799832891896 |
| Best lag | 0 (days) |
| perm_p | 0.8183632734530938 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.98, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.dubai.cams_no2` (2025-03..2026-09 archive window); `finance.LHA.DE.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.09381799832891896, n=392).

The best tested lag was 0 days with r=-0.09381799832891892.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long LHA**, hold 1d
- Entry: airquality.dubai.cams_no2 rolling_zscore_20d > 1 at close -> long LHA next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=58 hit_rate=0.4482758620689655 avg_return=-0.0015455614751381643 excess=-0.001731245237934159 sharpe_like=-0.6291196127504348 max_dd=-0.15249870705345614
- OOS (war period): n=20 hit=0.45 avg=0.00165125541722147
- Actionability: 2.98
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
