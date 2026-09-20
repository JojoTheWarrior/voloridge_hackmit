# R2-0002

| Field | Value |
|---|---|
| Mission id | `R2-0002` |
| Folder | `20260920-135-gdelt-gkg-tanker-share_x_finance-stng-log-return` |
| Indicators | `gdelt.gkg.tanker_share` × `finance.STNG.log_return` |
| n_obs | 390 |
| r | 0.013212886664982347 |
| Best lag | -4 (days) |
| perm_p | 0.908183632734531 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.58, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.tanker_share` (configured analysis window); `finance.STNG.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.013212886664982347, n=390).

The best tested lag was -4 days with r=-0.038321228975542.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long STNG**, hold 1d
- Entry: gdelt.gkg.tanker_share rolling_zscore_20d > 1 at close -> long STNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=28 hit_rate=0.5714285714285714 avg_return=0.005367640899435929 excess=0.0029223767659803186 sharpe_like=1.0883685885279304 max_dd=-0.14201295375382061
- OOS (war period): n=11 hit=0.45454545454545453 avg=-0.0016016118325253342
- Actionability: 4.58
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
