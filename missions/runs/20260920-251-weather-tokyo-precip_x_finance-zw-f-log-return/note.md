# R2-0155

| Field | Value |
|---|---|
| Mission id | `R2-0155` |
| Folder | `20260920-251-weather-tokyo-precip_x_finance-zw-f-log-return` |
| Indicators | `weather.tokyo.precip` × `finance.ZW=F.log_return` |
| n_obs | 387 |
| r | -0.07130213334577445 |
| Best lag | 9 (days) |
| perm_p | 0.6307385229540918 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.21, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.tokyo.precip` (configured analysis window); `finance.ZW=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.07130213334577445, n=387).

The best tested lag was 9 days with r=0.09667354637215281.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZW=F**, hold 9d
- Entry: weather.tokyo.precip rolling_zscore_20d > 1 at close -> long ZW=F next session
- Exit: close after 9 trading days (no overlapping entries)
- n_trades=22 hit_rate=0.5 avg_return=0.003729279048168105 excess=-0.0036395203139898986 sharpe_like=0.3669327161663317 max_dd=-0.1346310027911266
- OOS (war period): n=7 hit=0.2857142857142857 avg=-0.0050469476495422615
- Actionability: 1.21
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
