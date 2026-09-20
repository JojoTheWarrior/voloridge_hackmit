# R2-0067

| Field | Value |
|---|---|
| Mission id | `R2-0067` |
| Folder | `20260920-180-gdelt-gkg-oil-share_x_finance-ccl-log-return` |
| Indicators | `gdelt.gkg.oil_share` × `finance.CCL.log_return` |
| n_obs | 390 |
| r | -0.04729142880828751 |
| Best lag | 3 (days) |
| perm_p | 0.20159680638722555 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.91, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.oil_share` (configured analysis window); `finance.CCL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.04729142880828751, n=390).

The best tested lag was 3 days with r=-0.1059372972128522.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short CCL**, hold 3d
- Entry: gdelt.gkg.oil_share rolling_zscore_20d > 1 at close -> short CCL next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=40 hit_rate=0.45 avg_return=-0.0013407811391461105 excess=0.0009674671995969514 sharpe_like=-0.19467793978736136 max_dd=-0.2631027871585747
- OOS (war period): n=12 hit=0.75 avg=0.016118540320888736
- Actionability: 4.91
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
