# R2-0091

| Field | Value |
|---|---|
| Mission id | `R2-0091` |
| Folder | `20260920-195-gdelt-iran-usa-dyad-events_x_finance-ewy-log-return` |
| Indicators | `gdelt.iran_usa_dyad_events` × `finance.EWY.log_return` |
| n_obs | 390 |
| r | -0.02461575226746831 |
| Best lag | 1 (days) |
| perm_p | 0.5768463073852296 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.25, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.iran_usa_dyad_events` (configured analysis window); `finance.EWY.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.02461575226746831, n=390).

The best tested lag was 1 days with r=-0.051406451076942965.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short EWY**, hold 1d
- Entry: gdelt.iran_usa_dyad_events rolling_zscore_20d > 1 at close -> short EWY next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=56 hit_rate=0.375 avg_return=-0.005352531918648611 excess=-0.001727076330987556 sharpe_like=-1.1046389908563863 max_dd=-0.37801721887274387
- OOS (war period): n=17 hit=0.5882352941176471 avg=0.0007409818287445828
- Actionability: 2.25
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
