# R2-0124

| Field | Value |
|---|---|
| Mission id | `R2-0124` |
| Folder | `20260920-229-weather-houston-temp-max_x_finance-ratio-ttf-henryhub` |
| Indicators | `weather.houston.temp_max` × `finance.ratio.ttf_henryhub` |
| n_obs | 387 |
| r | 0.03454276175369487 |
| Best lag | 3 (days) |
| perm_p | 0.2714570858283433 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.31, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.houston.temp_max` (configured analysis window); `finance.ratio.ttf_henryhub` (configured analysis window) |

**Verdict:** supported (Pearson r=0.03454276175369487, n=387).

The best tested lag was 3 days with r=-0.09010510816820924.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ratio:ttf_henryhub**, hold 3d
- Entry: weather.houston.temp_max rolling_zscore_20d > 1 at close -> short ratio:ttf_henryhub next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=35 hit_rate=0.4 avg_return=-0.02635954938247834 excess=-0.012079717214372133 sharpe_like=-1.6207316416114323 max_dd=-0.7301018189440067
- OOS (war period): n=12 hit=0.5 avg=-0.002678712820643229
- Actionability: 2.31
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
