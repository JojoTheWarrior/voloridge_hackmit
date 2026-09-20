# R2-0111

| Field | Value |
|---|---|
| Mission id | `R2-0111` |
| Folder | `20260920-220-airquality-kuwait-cams-no2_x_finance-spread-gasoline-crack` |
| Indicators | `airquality.kuwait.cams_no2` × `finance.spread.gasoline_crack` |
| n_obs | 389 |
| r | 0.009726130775985553 |
| Best lag | -4 (days) |
| perm_p | 0.08982035928143713 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.04, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.kuwait.cams_no2` (2025-03..2026-09 archive window); `finance.spread.gasoline_crack` (configured analysis window) |

**Verdict:** supported (Pearson r=0.009726130775985553, n=389).

The best tested lag was -4 days with r=-0.15218140720702694.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short spread:gasoline_crack**, hold 1d
- Entry: airquality.kuwait.cams_no2 rolling_zscore_20d > 1 at close -> short spread:gasoline_crack next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=53 hit_rate=0.4716981132075472 avg_return=0.32405703922487655 excess=0.39160041332361717 sharpe_like=1.2398272200614917 max_dd=-1.5932124488119812
- OOS (war period): n=20 hit=0.5 avg=0.9622724533081055
- Actionability: 6.04
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
