# R2-0023

| Field | Value |
|---|---|
| Mission id | `R2-0023` |
| Folder | `20260920-148-gdelt-qat-conflict-events_x_finance-vg-log-return` |
| Indicators | `gdelt.qat.conflict_events` × `finance.VG.log_return` |
| n_obs | 390 |
| r | 0.10082490829465217 |
| Best lag | -1 (days) |
| perm_p | 0.2435129740518962 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.46, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.qat.conflict_events` (configured analysis window); `finance.VG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.10082490829465217, n=390).

The best tested lag was -1 days with r=0.1278114452899793.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long VG**, hold 1d
- Entry: gdelt.qat.conflict_events rolling_zscore_20d > 1 at close -> long VG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=50 hit_rate=0.56 avg_return=0.01424276904032795 excess=0.011829771505602273 sharpe_like=2.045239516596587 max_dd=-0.2174993423165914
- OOS (war period): n=15 hit=0.6 avg=0.03094748439450239
- Actionability: 7.46
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
