# R2-0044

| Field | Value |
|---|---|
| Mission id | `R2-0044` |
| Folder | `20260920-162-gdelt-irn-conflict-events_x_finance-mos-log-return` |
| Indicators | `gdelt.irn.conflict_events` × `finance.MOS.log_return` |
| n_obs | 390 |
| r | -0.03293594939559315 |
| Best lag | 9 (days) |
| perm_p | 0.14570858283433133 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.19, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.conflict_events` (configured analysis window); `finance.MOS.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.03293594939559315, n=390).

The best tested lag was 9 days with r=-0.1396621550348882.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long MOS**, hold 9d
- Entry: gdelt.irn.conflict_events rolling_zscore_20d > 1 at close -> long MOS next session
- Exit: close after 9 trading days (no overlapping entries)
- n_trades=24 hit_rate=0.5 avg_return=0.003881741625988866 excess=0.0018661548557757754 sharpe_like=0.24834740088872861 max_dd=-0.38385514848858504
- OOS (war period): n=9 hit=0.4444444444444444 avg=-0.013230566404292618
- Actionability: 2.19
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
