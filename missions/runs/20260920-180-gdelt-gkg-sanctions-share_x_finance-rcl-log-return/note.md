# R2-0068

| Field | Value |
|---|---|
| Mission id | `R2-0068` |
| Folder | `20260920-180-gdelt-gkg-sanctions-share_x_finance-rcl-log-return` |
| Indicators | `gdelt.gkg.sanctions_share` × `finance.RCL.log_return` |
| n_obs | 390 |
| r | -0.0603254081370455 |
| Best lag | 5 (days) |
| perm_p | 0.17564870259481039 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.32, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.sanctions_share` (configured analysis window); `finance.RCL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.0603254081370455, n=390).

The best tested lag was 5 days with r=-0.14114276470763082.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short RCL**, hold 5d
- Entry: gdelt.gkg.sanctions_share rolling_zscore_20d > 1 at close -> short RCL next session
- Exit: close after 5 trading days (no overlapping entries)
- n_trades=26 hit_rate=0.4230769230769231 avg_return=-0.004970370482478474 excess=-0.0005687362986085765 sharpe_like=-0.42621004732641476 max_dd=-0.3792825823693229
- OOS (war period): n=8 hit=0.5 avg=0.016869601348424676
- Actionability: 2.32
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
