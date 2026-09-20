# R2-0098

| Field | Value |
|---|---|
| Mission id | `R2-0098` |
| Folder | `20260920-202-gdelt-gkg-helium-share_x_finance-vg-log-return` |
| Indicators | `gdelt.gkg.helium_share` × `finance.VG.log_return` |
| n_obs | 390 |
| r | -0.014022575803997735 |
| Best lag | 4 (days) |
| perm_p | 0.2554890219560878 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.6, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.helium_share` (configured analysis window); `finance.VG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.014022575803997735, n=390).

The best tested lag was 4 days with r=0.15986491583712722.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long VG**, hold 4d
- Entry: gdelt.gkg.helium_share rolling_zscore_20d > 1 at close -> long VG next session
- Exit: close after 4 trading days (no overlapping entries)
- n_trades=5 hit_rate=1.0 avg_return=0.1321110088851012 excess=0.06909174161412214 sharpe_like=3.89272235617093 max_dd=0.0
- OOS (war period): n=1 hit=1.0 avg=0.1628817422979416
- Actionability: 7.6
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
