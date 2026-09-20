# R2-0147

| Field | Value |
|---|---|
| Mission id | `R2-0147` |
| Folder | `20260920-245-gdelt-gkg-fertilizer-share_x_finance-mos-log-return` |
| Indicators | `gdelt.gkg.fertilizer_share` × `finance.MOS.log_return` |
| n_obs | 390 |
| r | -0.09550171460422124 |
| Best lag | -9 (days) |
| perm_p | 0.2654690618762475 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.75, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.fertilizer_share` (configured analysis window); `finance.MOS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.09550171460422124, n=390).

The best tested lag was -9 days with r=-0.11717348600787045.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short MOS**, hold 1d
- Entry: gdelt.gkg.fertilizer_share rolling_zscore_20d > 1 at close -> short MOS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=45 hit_rate=0.6 avg_return=0.010388810600661928 excess=0.010711068897947599 sharpe_like=1.8731661391105945 max_dd=-0.1018572273763455
- OOS (war period): n=20 hit=0.6 avg=0.007367496338657293
- Actionability: 8.75
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
