# R2-0142

| Field | Value |
|---|---|
| Mission id | `R2-0142` |
| Folder | `20260920-242-gdelt-qat-conflict-events_x_finance-cf-log-return` |
| Indicators | `gdelt.qat.conflict_events` × `finance.CF.log_return` |
| n_obs | 390 |
| r | 0.12600527674011902 |
| Best lag | 3 (days) |
| perm_p | 0.03992015968063872 |
| Bonferroni | 0.8383233532934131 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 9.79, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.qat.conflict_events` (configured analysis window); `finance.CF.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.12600527674011902, n=390).

The best tested lag was 3 days with r=0.15730651518163905.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 3d
- Entry: gdelt.qat.conflict_events rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=36 hit_rate=0.6944444444444444 avg_return=0.013148299070610372 excess=0.008118166780634508 sharpe_like=2.2834651414607046 max_dd=-0.10809476674504293
- OOS (war period): n=12 hit=0.5833333333333334 avg=0.010493182957391342
- Actionability: 9.79
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
