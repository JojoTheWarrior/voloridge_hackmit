# R2-0118

| Field | Value |
|---|---|
| Mission id | `R2-0118` |
| Folder | `20260920-225-weather-tokyo-precip_x_finance-fro-log-return` |
| Indicators | `weather.tokyo.precip` × `finance.FRO.log_return` |
| n_obs | 387 |
| r | -0.01813188814395473 |
| Best lag | -10 (days) |
| perm_p | 0.6946107784431138 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.6, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.tokyo.precip` (configured analysis window); `finance.FRO.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.01813188814395473, n=387).

The best tested lag was -10 days with r=0.09762544821729059.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long FRO**, hold 1d
- Entry: weather.tokyo.precip rolling_zscore_20d > 1 at close -> long FRO next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=39 hit_rate=0.5897435897435898 avg_return=0.007279242333964848 excess=0.003540765683801705 sharpe_like=1.9757226465167776 max_dd=-0.05968311310136987
- OOS (war period): n=13 hit=0.46153846153846156 avg=0.0009705854911119527
- Actionability: 5.6
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
