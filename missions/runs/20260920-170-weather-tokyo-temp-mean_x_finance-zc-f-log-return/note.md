# R2-0057

| Field | Value |
|---|---|
| Mission id | `R2-0057` |
| Folder | `20260920-170-weather-tokyo-temp-mean_x_finance-zc-f-log-return` |
| Indicators | `weather.tokyo.temp_mean` × `finance.ZC=F.log_return` |
| n_obs | 387 |
| r | 0.01905589219354483 |
| Best lag | -7 (days) |
| perm_p | 1.0 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.25, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.tokyo.temp_mean` (configured analysis window); `finance.ZC=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.01905589219354483, n=387).

The best tested lag was -7 days with r=0.02225682878857625.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZC=F**, hold 1d
- Entry: weather.tokyo.temp_mean rolling_zscore_20d > 1 at close -> long ZC=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=59 hit_rate=0.4745762711864407 avg_return=-0.0005114573543096122 excess=-0.000996560535591802 sharpe_like=-0.3274207301927105 max_dd=-0.09707583345186366
- OOS (war period): n=28 hit=0.5357142857142857 avg=0.0008745216491414123
- Actionability: 1.25
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
