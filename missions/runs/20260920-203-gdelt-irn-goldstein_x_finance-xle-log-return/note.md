# R2-0103

| Field | Value |
|---|---|
| Mission id | `R2-0103` |
| Folder | `20260920-203-gdelt-irn-goldstein_x_finance-xle-log-return` |
| Indicators | `gdelt.irn.goldstein` × `finance.XLE.log_return` |
| n_obs | 390 |
| r | -0.05868901838777052 |
| Best lag | -5 (days) |
| perm_p | 0.029940119760479042 |
| Bonferroni | 0.6287425149700598 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.12, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.goldstein` (configured analysis window); `finance.XLE.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.05868901838777052, n=390).

The best tested lag was -5 days with r=-0.15114318889375838.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long XLE**, hold 1d
- Entry: gdelt.irn.goldstein rolling_zscore_20d > 1 at close -> long XLE next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=0.5555555555555556 avg_return=0.0035655559614559498 excess=0.002459780504336822 sharpe_like=1.5901004553438711 max_dd=-0.04728417038551758
- OOS (war period): n=18 hit=0.5 avg=0.00034318961614405855
- Actionability: 5.12
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
