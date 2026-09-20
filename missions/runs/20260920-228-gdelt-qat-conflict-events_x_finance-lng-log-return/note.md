# R2-0122

| Field | Value |
|---|---|
| Mission id | `R2-0122` |
| Folder | `20260920-228-gdelt-qat-conflict-events_x_finance-lng-log-return` |
| Indicators | `gdelt.qat.conflict_events` × `finance.LNG.log_return` |
| n_obs | 390 |
| r | 0.14116898603817413 |
| Best lag | 0 (days) |
| perm_p | 0.18962075848303392 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.38, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.qat.conflict_events` (configured analysis window); `finance.LNG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.14116898603817413, n=390).

The best tested lag was 0 days with r=0.1411689860381741.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long LNG**, hold 1d
- Entry: gdelt.qat.conflict_events rolling_zscore_20d > 1 at close -> long LNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=50 hit_rate=0.54 avg_return=0.0020460925296210217 excess=0.001282455570251056 sharpe_like=0.724797934934013 max_dd=-0.1054373289591809
- OOS (war period): n=15 hit=0.6 avg=0.0036168739271245087
- Actionability: 7.38
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
