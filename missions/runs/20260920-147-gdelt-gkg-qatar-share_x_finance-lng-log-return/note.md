# R2-0022

| Field | Value |
|---|---|
| Mission id | `R2-0022` |
| Folder | `20260920-147-gdelt-gkg-qatar-share_x_finance-lng-log-return` |
| Indicators | `gdelt.gkg.qatar_share` × `finance.LNG.log_return` |
| n_obs | 390 |
| r | 0.12491499394398034 |
| Best lag | -2 (days) |
| perm_p | 0.11177644710578842 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.34, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.qatar_share` (configured analysis window); `finance.LNG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.12491499394398034, n=390).

The best tested lag was -2 days with r=0.13288178609869733.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long LNG**, hold 1d
- Entry: gdelt.gkg.qatar_share rolling_zscore_20d > 1 at close -> long LNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=37 hit_rate=0.5405405405405406 avg_return=0.0016831132092643675 excess=0.0009194762498944017 sharpe_like=0.8830085339030344 max_dd=-0.048262215493984684
- OOS (war period): n=7 hit=0.42857142857142855 avg=-0.001634004200447173
- Actionability: 4.34
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
