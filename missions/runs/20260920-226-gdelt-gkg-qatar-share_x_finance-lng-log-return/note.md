# R2-0120

| Field | Value |
|---|---|
| Mission id | `R2-0120` |
| Folder | `20260920-226-gdelt-gkg-qatar-share_x_finance-lng-log-return` |
| Indicators | `gdelt.gkg.qatar_share` × `finance.LNG.log_return` |
| n_obs | 390 |
| r | 0.12491499394398034 |
| Best lag | -2 (days) |
| perm_p | 0.18762475049900199 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.94, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.qatar_share` (configured analysis window); `finance.LNG.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.12491499394398034, n=390).

The best tested lag was -2 days with r=0.13288178609869733.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short LNG**, hold 1d
- Entry: gdelt.gkg.qatar_share rolling_zscore_20d > 1 at close -> short LNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=37 hit_rate=0.4594594594594595 avg_return=-0.0016831132092643675 excess=-0.0009194762498944017 sharpe_like=-0.8830085339030344 max_dd=-0.07801787534599613
- OOS (war period): n=7 hit=0.5714285714285714 avg=0.001634004200447173
- Actionability: 3.94
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
