# R2-0026

| Field | Value |
|---|---|
| Mission id | `R2-0026` |
| Folder | `20260920-149-weather-london-temp-min_x_finance-ttf-f-close` |
| Indicators | `weather.london.temp_min` × `finance.TTF=F.close` |
| n_obs | 387 |
| r | 0.0017461291638643517 |
| Best lag | 2 (days) |
| perm_p | 0.6806387225548902 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.london.temp_min` (configured analysis window); `finance.TTF=F.close` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0017461291638643517, n=387).

The best tested lag was 2 days with r=0.06181680659239148.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long TTF=F**, hold 2d
- Entry: weather.london.temp_min rolling_zscore_20d > 1 at close -> long TTF=F next session
- Exit: close after 2 trading days (no overlapping entries)
- n_trades=53 hit_rate=0.4716981132075472 avg_return=0.011573503855114341 excess=0.006657569096168542 sharpe_like=1.17349973372121 max_dd=-0.2639914876444619
- OOS (war period): n=19 hit=0.47368421052631576 avg=0.013925795752431832
- Actionability: 6.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
