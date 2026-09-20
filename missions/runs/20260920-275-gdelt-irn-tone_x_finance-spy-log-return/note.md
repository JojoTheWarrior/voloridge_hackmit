# R2-0190

| Field | Value |
|---|---|
| Mission id | `R2-0190` |
| Folder | `20260920-275-gdelt-irn-tone_x_finance-spy-log-return` |
| Indicators | `gdelt.irn.tone` × `finance.SPY.log_return` |
| n_obs | 390 |
| r | 0.07010269115858245 |
| Best lag | -9 (days) |
| perm_p | 0.8363273453093812 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.87, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.tone` (configured analysis window); `finance.SPY.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.07010269115858245, n=390).

The best tested lag was -9 days with r=-0.0728276664436404.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long SPY**, hold 1d
- Entry: gdelt.irn.tone rolling_zscore_20d > 1 at close -> long SPY next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=0.5370370370370371 avg_return=-0.0004475884171723407 excess=-0.0013049384169167536 sharpe_like=-0.312426942815818 max_dd=-0.09290621675157851
- OOS (war period): n=18 hit=0.5 avg=0.0006816773747603441
- Actionability: 1.87
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
