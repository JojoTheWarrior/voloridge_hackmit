# R2-0079

| Field | Value |
|---|---|
| Mission id | `R2-0079` |
| Folder | `20260920-186-gdelt-gkg-ceasefire-share_x_finance-ksa-log-return` |
| Indicators | `gdelt.gkg.ceasefire_share` × `finance.KSA.log_return` |
| n_obs | 390 |
| r | 0.019997505997884572 |
| Best lag | -5 (days) |
| perm_p | 0.8822355289421158 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.99, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.ceasefire_share` (configured analysis window); `finance.KSA.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.019997505997884572, n=390).

The best tested lag was -5 days with r=0.051545704066662056.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long KSA**, hold 1d
- Entry: gdelt.gkg.ceasefire_share rolling_zscore_20d > 1 at close -> long KSA next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=29 hit_rate=0.4827586206896552 avg_return=-0.0011266831883497343 excess=-0.001004651064483081 sharpe_like=-0.5885708086716985 max_dd=-0.0552787146814786
- OOS (war period): n=14 hit=0.5 avg=0.00015710840183863484
- Actionability: 0.99
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
