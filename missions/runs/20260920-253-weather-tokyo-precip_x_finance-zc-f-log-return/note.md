# R2-0156

| Field | Value |
|---|---|
| Mission id | `R2-0156` |
| Folder | `20260920-253-weather-tokyo-precip_x_finance-zc-f-log-return` |
| Indicators | `weather.tokyo.precip` × `finance.ZC=F.log_return` |
| n_obs | 387 |
| r | -0.05354488207278363 |
| Best lag | 6 (days) |
| perm_p | 0.10578842315369262 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.33, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.tokyo.precip` (configured analysis window); `finance.ZC=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.05354488207278363, n=387).

The best tested lag was 6 days with r=0.14673245448078984.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZC=F**, hold 6d
- Entry: weather.tokyo.precip rolling_zscore_20d > 1 at close -> long ZC=F next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=24 hit_rate=0.5 avg_return=0.003051733551650407 excess=0.00025378622538520506 sharpe_like=0.45005170698703484 max_dd=-0.15803039955953946
- OOS (war period): n=8 hit=0.5 avg=0.009594126768758426
- Actionability: 5.33
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
