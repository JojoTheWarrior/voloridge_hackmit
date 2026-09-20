# R2-0186

| Field | Value |
|---|---|
| Mission id | `R2-0186` |
| Folder | `20260920-273-gdelt-irn-conflict-events_x_finance-ita-log-return` |
| Indicators | `gdelt.irn.conflict_events` × `finance.ITA.log_return` |
| n_obs | 390 |
| r | -0.062244961446667885 |
| Best lag | 6 (days) |
| perm_p | 0.28542914171656686 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.85, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.conflict_events` (configured analysis window); `finance.ITA.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.062244961446667885, n=390).

The best tested lag was 6 days with r=-0.10490644025510748.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ITA**, hold 6d
- Entry: gdelt.irn.conflict_events rolling_zscore_20d > 1 at close -> long ITA next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=28 hit_rate=0.5 avg_return=0.006713706963436737 excess=0.00032171740122123507 sharpe_like=1.0606280071800274 max_dd=-0.08539651682095584
- OOS (war period): n=8 hit=0.375 avg=-7.293036938653408e-05
- Actionability: 6.85
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
