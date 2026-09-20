# R2-0107

| Field | Value |
|---|---|
| Mission id | `R2-0107` |
| Folder | `20260920-219-gdelt-gkg-sanctions-share_x_finance-spread-brent-wti` |
| Indicators | `gdelt.gkg.sanctions_share` × `finance.spread.brent_wti` |
| n_obs | 390 |
| r | 0.11231786990274643 |
| Best lag | 0 (days) |
| perm_p | 0.25149700598802394 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.58, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.sanctions_share` (configured analysis window); `finance.spread.brent_wti` (configured analysis window) |

**Verdict:** supported (Pearson r=0.11231786990274643, n=390).

The best tested lag was 0 days with r=0.11231786990274639.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long spread:brent_wti**, hold 1d
- Entry: gdelt.gkg.sanctions_share rolling_zscore_20d > 1 at close -> long spread:brent_wti next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=43 hit_rate=0.5116279069767442 avg_return=-0.06302234738372094 excess=-0.06385351542222541 sharpe_like=-0.6892939407084491 max_dd=-1.4275799886176703
- OOS (war period): n=12 hit=0.4166666666666667 avg=-0.30499903361002606
- Actionability: 0.58
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
