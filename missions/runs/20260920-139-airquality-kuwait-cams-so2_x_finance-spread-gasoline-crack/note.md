# R2-0014

| Field | Value |
|---|---|
| Mission id | `R2-0014` |
| Folder | `20260920-139-airquality-kuwait-cams-so2_x_finance-spread-gasoline-crack` |
| Indicators | `airquality.kuwait.cams_so2` × `finance.spread.gasoline_crack` |
| n_obs | 389 |
| r | -0.0012686637945452696 |
| Best lag | -4 (days) |
| perm_p | 0.09580838323353294 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.19, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `airquality.kuwait.cams_so2` (2025-03..2026-09 archive window); `finance.spread.gasoline_crack` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.0012686637945452696, n=389).

The best tested lag was -4 days with r=-0.16607365400506857.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short spread:gasoline_crack**, hold 1d
- Entry: airquality.kuwait.cams_so2 rolling_zscore_20d > 1 at close -> short spread:gasoline_crack next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=49 hit_rate=0.46938775510204084 avg_return=-0.04461195030990912 excess=0.0229314237888315 sharpe_like=-0.15716999732938844 max_dd=-1.4456162869126532
- OOS (war period): n=18 hit=0.4444444444444444 avg=0.039646546045939125
- Actionability: 5.19
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
