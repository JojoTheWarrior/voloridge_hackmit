# R2-0027

| Field | Value |
|---|---|
| Mission id | `R2-0027` |
| Folder | `20260920-150-weather-doha-temp-max_x_finance-ratio-ttf-henryhub` |
| Indicators | `weather.doha.temp_max` × `finance.ratio.ttf_henryhub` |
| n_obs | 387 |
| r | 0.008241284203048618 |
| Best lag | 6 (days) |
| perm_p | 0.6447105788423154 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.35, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.doha.temp_max` (configured analysis window); `finance.ratio.ttf_henryhub` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.008241284203048618, n=387).

The best tested lag was 6 days with r=-0.05400793816209866.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ratio:ttf_henryhub**, hold 6d
- Entry: weather.doha.temp_max rolling_zscore_20d > 1 at close -> long ratio:ttf_henryhub next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=34 hit_rate=0.6470588235294118 avg_return=0.018747010694840572 excess=-0.008538157594347996 sharpe_like=0.8952205755851643 max_dd=-0.36492757330312975
- OOS (war period): n=14 hit=0.7142857142857143 avg=0.04789318915734851
- Actionability: 5.35
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
