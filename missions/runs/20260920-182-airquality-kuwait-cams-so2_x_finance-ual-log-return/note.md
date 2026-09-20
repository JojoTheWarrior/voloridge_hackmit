# R2-0071

| Field | Value |
|---|---|
| Mission id | `R2-0071` |
| Folder | `20260920-182-airquality-kuwait-cams-so2_x_finance-ual-log-return` |
| Indicators | `airquality.kuwait.cams_so2` × `finance.UAL.log_return` |
| n_obs | 389 |
| r | 0.07101231710509848 |
| Best lag | 0 (days) |
| perm_p | 0.9281437125748503 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.42, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.kuwait.cams_so2` (2025-03..2026-09 archive window); `finance.UAL.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.07101231710509848, n=389).

The best tested lag was 0 days with r=0.0710123171050985.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short UAL**, hold 1d
- Entry: airquality.kuwait.cams_so2 rolling_zscore_20d > 1 at close -> short UAL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=49 hit_rate=0.5918367346938775 avg_return=-0.007610436387915994 excess=-0.0061503373333729235 sharpe_like=-1.0966222333631102 max_dd=-0.4482941488944915
- OOS (war period): n=18 hit=0.6111111111111112 avg=-0.003176117757937259
- Actionability: 1.42
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
