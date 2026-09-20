# R2-0083

| Field | Value |
|---|---|
| Mission id | `R2-0083` |
| Folder | `20260920-189-gdelt-gkg-cyber-share_x_finance-qqq-log-return` |
| Indicators | `gdelt.gkg.cyber_share` × `finance.QQQ.log_return` |
| n_obs | 390 |
| r | -0.023079885706053987 |
| Best lag | 10 (days) |
| perm_p | 0.8562874251497006 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.78, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.cyber_share` (configured analysis window); `finance.QQQ.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.023079885706053987, n=390).

The best tested lag was 10 days with r=0.07532039476981588.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short QQQ**, hold 10d
- Entry: gdelt.gkg.cyber_share rolling_zscore_20d > 1 at close -> short QQQ next session
- Exit: close after 10 trading days (no overlapping entries)
- n_trades=24 hit_rate=0.375 avg_return=-0.013614102332744562 excess=-0.002114261846996743 sharpe_like=-2.202661589051941 max_dd=-0.3051747310711692
- OOS (war period): n=8 hit=0.625 avg=-0.00848629472882556
- Actionability: 1.78
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
