# R2-0069

| Field | Value |
|---|---|
| Mission id | `R2-0069` |
| Folder | `20260920-181-gdelt-gkg-qatar-share_x_finance-lha-de-log-return` |
| Indicators | `gdelt.gkg.qatar_share` × `finance.LHA.DE.log_return` |
| n_obs | 392 |
| r | -0.10291736365837711 |
| Best lag | 0 (days) |
| perm_p | 0.5289421157684631 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.81, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.qatar_share` (configured analysis window); `finance.LHA.DE.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.10291736365837711, n=392).

The best tested lag was 0 days with r=-0.10291736365837721.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short LHA**, hold 1d
- Entry: gdelt.gkg.qatar_share rolling_zscore_20d > 1 at close -> short LHA next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=37 hit_rate=0.5135135135135135 avg_return=0.0019267024062354801 excess=0.002112386169031475 sharpe_like=0.48764526759691723 max_dd=-0.10328459648854316
- OOS (war period): n=7 hit=0.42857142857142855 avg=0.001318351057389406
- Actionability: 6.81
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
