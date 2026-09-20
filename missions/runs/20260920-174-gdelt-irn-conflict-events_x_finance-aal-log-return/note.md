# R2-0062

| Field | Value |
|---|---|
| Mission id | `R2-0062` |
| Folder | `20260920-174-gdelt-irn-conflict-events_x_finance-aal-log-return` |
| Indicators | `gdelt.irn.conflict_events` × `finance.AAL.log_return` |
| n_obs | 390 |
| r | -0.08968081550825518 |
| Best lag | -1 (days) |
| perm_p | 0.10379241516966067 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.02, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.conflict_events` (configured analysis window); `finance.AAL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.08968081550825518, n=390).

The best tested lag was -1 days with r=-0.11381232565487663.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short AAL**, hold 1d
- Entry: gdelt.irn.conflict_events rolling_zscore_20d > 1 at close -> short AAL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=62 hit_rate=0.5483870967741935 avg_return=0.0003196529398060502 excess=0.0009717496219780349 sharpe_like=0.05817517552265177 max_dd=-0.3058431779133972
- OOS (war period): n=21 hit=0.7142857142857143 avg=0.007323800009221361
- Actionability: 6.02
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
