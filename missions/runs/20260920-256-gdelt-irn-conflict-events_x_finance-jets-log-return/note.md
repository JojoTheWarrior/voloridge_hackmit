# R2-0162

| Field | Value |
|---|---|
| Mission id | `R2-0162` |
| Folder | `20260920-256-gdelt-irn-conflict-events_x_finance-jets-log-return` |
| Indicators | `gdelt.irn.conflict_events` × `finance.JETS.log_return` |
| n_obs | 390 |
| r | -0.10319330604356841 |
| Best lag | -1 (days) |
| perm_p | 0.03992015968063872 |
| Bonferroni | 0.8383233532934131 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.66, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.conflict_events` (configured analysis window); `finance.JETS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.10319330604356841, n=390).

The best tested lag was -1 days with r=-0.120774088086039.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short JETS**, hold 1d
- Entry: gdelt.irn.conflict_events rolling_zscore_20d > 1 at close -> short JETS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=62 hit_rate=0.5161290322580645 avg_return=-0.002110538762829474 excess=-0.0011962718122703088 sharpe_like=-0.5569356129496584 max_dd=-0.2531530640056293
- OOS (war period): n=21 hit=0.5714285714285714 avg=0.002544566859949458
- Actionability: 3.66
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
