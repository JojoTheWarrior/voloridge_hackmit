# R2-0156

| Field | Value |
|---|---|
| Mission id | `R2-0156` |
| Folder | `20260920-252-weather-tokyo-precip_x_finance-vix-log-return` |
| Indicators | `weather.tokyo.precip` × `finance.^VIX.log_return` |
| n_obs | 65 |
| r | -0.09372580614472337 |
| Best lag | -3 (days) |
| perm_p | 0.8562874251497006 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.tokyo.precip` (configured analysis window); `finance.^VIX.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.09372580614472337, n=65).

The best tested lag was -3 days with r=0.1621034118390975.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ^VIX**, hold 1d
- Entry: weather.tokyo.precip rolling_zscore_20d > 1 at close -> long ^VIX next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=39 hit_rate=0.3333333333333333 avg_return=-0.021816287678541886 excess=-0.024024373781032667 sharpe_like=-2.740845877390754 max_dd=-0.6251370494870965
- OOS (war period): n=13 hit=0.38461538461538464 avg=-0.009659236074787811
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
