# R2-0180

| Field | Value |
|---|---|
| Mission id | `R2-0180` |
| Folder | `20260920-267-gdelt-gkg-ceasefire-share_x_finance-ksa-log-return` |
| Indicators | `gdelt.gkg.ceasefire_share` × `finance.KSA.log_return` |
| n_obs | 390 |
| r | 0.019997505997884572 |
| Best lag | 8 (days) |
| perm_p | 0.15169660678642716 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.65, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.ceasefire_share` (configured analysis window); `finance.KSA.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.019997505997884572, n=390).

The best tested lag was 8 days with r=-0.11640761191557322.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short KSA**, hold 8d
- Entry: gdelt.gkg.ceasefire_share rolling_zscore_20d > 1 at close -> short KSA next session
- Exit: close after 8 trading days (no overlapping entries)
- n_trades=19 hit_rate=0.5789473684210527 avg_return=-0.0005520496389615813 excess=-0.001570078707360797 sharpe_like=-0.11818634518804091 max_dd=-0.11869136426121263
- OOS (war period): n=8 hit=0.5 avg=-0.004574317994724811
- Actionability: 1.65
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
