# R2-0094

| Field | Value |
|---|---|
| Mission id | `R2-0094` |
| Folder | `20260920-196-finance-ratio-gold-oil_x_finance-eem-log-return` |
| Indicators | `finance.ratio.gold_oil` × `finance.EEM.log_return` |
| n_obs | 389 |
| r | 0.3186312169871301 |
| Best lag | 0 (days) |
| perm_p | 0.029940119760479042 |
| Bonferroni | 0.6287425149700598 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 6.22, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.ratio.gold_oil` (configured analysis window); `finance.EEM.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.3186312169871301, n=389).

The best tested lag was 0 days with r=0.31863121698713004.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short EEM**, hold 1d
- Entry: finance.ratio.gold_oil rolling_zscore_20d > 1 at close -> short EEM next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=48 hit_rate=0.5625 avg_return=0.0004140175530476173 excess=0.0015539265957878314 sharpe_like=0.13560044913016794 max_dd=-0.16694584221053899
- OOS (war period): n=18 hit=0.5555555555555556 avg=0.004839324671744872
- Actionability: 6.22
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
