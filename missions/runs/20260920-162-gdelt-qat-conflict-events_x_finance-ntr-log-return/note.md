# R2-0043

| Field | Value |
|---|---|
| Mission id | `R2-0043` |
| Folder | `20260920-162-gdelt-qat-conflict-events_x_finance-ntr-log-return` |
| Indicators | `gdelt.qat.conflict_events` × `finance.NTR.log_return` |
| n_obs | 390 |
| r | -0.0036529526153294494 |
| Best lag | 3 (days) |
| perm_p | 0.31736526946107785 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.76, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.qat.conflict_events` (configured analysis window); `finance.NTR.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.0036529526153294494, n=390).

The best tested lag was 3 days with r=0.113360747972262.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long NTR**, hold 3d
- Entry: gdelt.qat.conflict_events rolling_zscore_20d > 1 at close -> long NTR next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=36 hit_rate=0.6111111111111112 avg_return=0.011020895826630914 excess=0.007117324685122188 sharpe_like=1.9842105139025692 max_dd=-0.06850902860547514
- OOS (war period): n=12 hit=0.5833333333333334 avg=0.00979733673743514
- Actionability: 8.76
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
