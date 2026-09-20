# R2-0169

| Field | Value |
|---|---|
| Mission id | `R2-0169` |
| Folder | `20260920-262-gdelt-gkg-tanker-share_x_finance-jets-log-return` |
| Indicators | `gdelt.gkg.tanker_share` × `finance.JETS.log_return` |
| n_obs | 390 |
| r | -0.03481459834991517 |
| Best lag | 3 (days) |
| perm_p | 0.5728542914171657 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.tanker_share` (configured analysis window); `finance.JETS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.03481459834991517, n=390).

The best tested lag was 3 days with r=-0.07464684839996721.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short JETS**, hold 3d
- Entry: gdelt.gkg.tanker_share rolling_zscore_20d > 1 at close -> short JETS next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=25 hit_rate=0.48 avg_return=-0.00728545657030133 excess=-0.00454050431039694 sharpe_like=-0.9212573587323643 max_dd=-0.20725111028420973
- OOS (war period): n=10 hit=0.5 avg=-0.005321318256755548
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
