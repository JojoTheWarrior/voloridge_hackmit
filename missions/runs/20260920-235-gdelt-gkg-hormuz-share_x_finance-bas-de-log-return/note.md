# R2-0133

| Field | Value |
|---|---|
| Mission id | `R2-0133` |
| Folder | `20260920-235-gdelt-gkg-hormuz-share_x_finance-bas-de-log-return` |
| Indicators | `gdelt.gkg.hormuz_share` × `finance.BAS.DE.log_return` |
| n_obs | 392 |
| r | 0.09414210444297826 |
| Best lag | -3 (days) |
| perm_p | 0.3473053892215569 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 9.1, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.hormuz_share` (configured analysis window); `finance.BAS.DE.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.09414210444297826, n=392).

The best tested lag was -3 days with r=0.12218459574376032.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long BAS**, hold 1d
- Entry: gdelt.gkg.hormuz_share rolling_zscore_20d > 1 at close -> long BAS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=5 hit_rate=1.0 avg_return=0.018368620749180886 excess=0.015730441023064246 sharpe_like=3.208921153422383 max_dd=0.0
- OOS (war period): n=5 hit=1.0 avg=0.018368620749180886
- Actionability: 9.1
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
