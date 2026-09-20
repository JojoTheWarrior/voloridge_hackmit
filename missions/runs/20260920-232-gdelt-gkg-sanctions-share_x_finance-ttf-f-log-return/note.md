# R2-0129

| Field | Value |
|---|---|
| Mission id | `R2-0129` |
| Folder | `20260920-232-gdelt-gkg-sanctions-share_x_finance-ttf-f-log-return` |
| Indicators | `gdelt.gkg.sanctions_share` × `finance.TTF=F.log_return` |
| n_obs | 391 |
| r | 0.03655663054514233 |
| Best lag | 6 (days) |
| perm_p | 0.14570858283433133 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.42, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.sanctions_share` (configured analysis window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.03655663054514233, n=391).

The best tested lag was 6 days with r=0.14172405836210847.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long TTF=F**, hold 6d
- Entry: gdelt.gkg.sanctions_share rolling_zscore_20d > 1 at close -> long TTF=F next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=25 hit_rate=0.48 avg_return=0.02512793720709837 excess=0.009460162150457422 sharpe_like=0.8387801046726193 max_dd=-0.24974059571865193
- OOS (war period): n=8 hit=0.625 avg=0.020421560347971615
- Actionability: 2.42
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
