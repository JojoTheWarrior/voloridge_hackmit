# R2-0045

| Field | Value |
|---|---|
| Mission id | `R2-0045` |
| Folder | `20260920-163-gdelt-gkg-tanker-share_x_finance-zc-f-log-return` |
| Indicators | `gdelt.gkg.tanker_share` × `finance.ZC=F.log_return` |
| n_obs | 390 |
| r | 0.0560470429081703 |
| Best lag | -5 (days) |
| perm_p | 0.0718562874251497 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.07, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.tanker_share` (configured analysis window); `finance.ZC=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0560470429081703, n=390).

The best tested lag was -5 days with r=0.12235796352726018.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZC=F**, hold 1d
- Entry: gdelt.gkg.tanker_share rolling_zscore_20d > 1 at close -> long ZC=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=28 hit_rate=0.39285714285714285 avg_return=-0.0033093098598847254 excess=-0.0037588806595267267 sharpe_like=-1.5824431736116864 max_dd=-0.11621216642018095
- OOS (war period): n=11 hit=0.5454545454545454 avg=-0.0010176033369376678
- Actionability: 0.07
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
