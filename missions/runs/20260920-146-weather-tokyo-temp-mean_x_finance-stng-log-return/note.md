# R2-0020

| Field | Value |
|---|---|
| Mission id | `R2-0020` |
| Folder | `20260920-146-weather-tokyo-temp-mean_x_finance-stng-log-return` |
| Indicators | `weather.tokyo.temp_mean` × `finance.STNG.log_return` |
| n_obs | 387 |
| r | 0.02121903564330927 |
| Best lag | 3 (days) |
| perm_p | 0.43313373253493015 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.74, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.tokyo.temp_mean` (configured analysis window); `finance.STNG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.02121903564330927, n=387).

The best tested lag was 3 days with r=0.05095269923029228.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long STNG**, hold 3d
- Entry: weather.tokyo.temp_mean rolling_zscore_20d > 1 at close -> long STNG next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=38 hit_rate=0.5263157894736842 avg_return=0.008695873266687651 excess=0.0013887535810598664 sharpe_like=1.6639068612101175 max_dd=-0.09524375997079604
- OOS (war period): n=17 hit=0.35294117647058826 avg=-0.0005354609357590951
- Actionability: 4.74
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
