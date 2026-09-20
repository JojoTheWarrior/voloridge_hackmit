# R2-0104

| Field | Value |
|---|---|
| Mission id | `R2-0104` |
| Folder | `20260920-202-gdelt-irn-conflict-events_x_finance-dht-log-return` |
| Indicators | `gdelt.irn.conflict_events` × `finance.DHT.log_return` |
| n_obs | 390 |
| r | -0.03323384399985936 |
| Best lag | 6 (days) |
| perm_p | 0.4590818363273453 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.69, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.conflict_events` (configured analysis window); `finance.DHT.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.03323384399985936, n=390).

The best tested lag was 6 days with r=-0.08153440077985158.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long DHT**, hold 6d
- Entry: gdelt.irn.conflict_events rolling_zscore_20d > 1 at close -> long DHT next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=28 hit_rate=0.6428571428571429 avg_return=0.01723813420780201 excess=0.003388405284237197 sharpe_like=1.6848322378790876 max_dd=-0.0897437832053396
- OOS (war period): n=8 hit=0.75 avg=0.02722164612318065
- Actionability: 8.69
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
