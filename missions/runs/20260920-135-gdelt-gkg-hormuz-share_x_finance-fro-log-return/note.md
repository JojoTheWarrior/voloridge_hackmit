# R2-0001

| Field | Value |
|---|---|
| Mission id | `R2-0001` |
| Folder | `20260920-135-gdelt-gkg-hormuz-share_x_finance-fro-log-return` |
| Indicators | `gdelt.gkg.hormuz_share` × `finance.FRO.log_return` |
| n_obs | 390 |
| r | 0.012569750680305716 |
| Best lag | -4 (days) |
| perm_p | 0.6427145708582834 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.58, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.hormuz_share` (configured analysis window); `finance.FRO.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.012569750680305716, n=390).

The best tested lag was -4 days with r=0.08961804845500293.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long FRO**, hold 1d
- Entry: gdelt.gkg.hormuz_share rolling_zscore_20d > 1 at close -> long FRO next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=5 hit_rate=0.4 avg_return=0.0076151327323691785 excess=0.004965383821533249 sharpe_like=0.7101513809422382 max_dd=-0.03107485496264728
- OOS (war period): n=5 hit=0.4 avg=0.0076151327323691785
- Actionability: 4.58
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
