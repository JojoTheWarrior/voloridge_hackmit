# R2-0073

| Field | Value |
|---|---|
| Mission id | `R2-0073` |
| Folder | `20260920-183-finance-spread-gasoline-crack_x_finance-ual-log-return` |
| Indicators | `finance.spread.gasoline_crack` × `finance.UAL.log_return` |
| n_obs | 389 |
| r | 0.04222873991552367 |
| Best lag | -9 (days) |
| perm_p | 0.24151696606786427 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.08, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.spread.gasoline_crack` (configured analysis window); `finance.UAL.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.04222873991552367, n=389).

The best tested lag was -9 days with r=0.14266938726976833.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short UAL**, hold 1d
- Entry: finance.spread.gasoline_crack rolling_zscore_20d > 1 at close -> short UAL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=48 hit_rate=0.4583333333333333 avg_return=-0.004124805402936182 excess=-0.002525572681080012 sharpe_like=-1.2072685097789446 max_dd=-0.24265048941243983
- OOS (war period): n=20 hit=0.45 avg=-0.003336597209345882
- Actionability: 0.08
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
