# R2-0005

| Field | Value |
|---|---|
| Mission id | `R2-0005` |
| Folder | `20260920-136-gdelt-irn-tone_x_finance-xle-log-return` |
| Indicators | `gdelt.irn.tone` × `finance.XLE.log_return` |
| n_obs | 390 |
| r | -0.09417089513913578 |
| Best lag | -2 (days) |
| perm_p | 0.1317365269461078 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.48, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.tone` (configured analysis window); `finance.XLE.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.09417089513913578, n=390).

The best tested lag was -2 days with r=-0.13190158214258624.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long XLE**, hold 1d
- Entry: gdelt.irn.tone rolling_zscore_20d > 1 at close -> long XLE next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=0.6481481481481481 avg_return=0.0017537472843716958 excess=0.0006479718272525679 sharpe_like=0.755262223253963 max_dd=-0.10379662504742426
- OOS (war period): n=18 hit=0.5 avg=0.0015884446228868138
- Actionability: 8.48
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
