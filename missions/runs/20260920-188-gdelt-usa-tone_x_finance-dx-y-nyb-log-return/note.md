# R2-0082

| Field | Value |
|---|---|
| Mission id | `R2-0082` |
| Folder | `20260920-188-gdelt-usa-tone_x_finance-dx-y-nyb-log-return` |
| Indicators | `gdelt.usa.tone` × `finance.DX-Y.NYB.log_return` |
| n_obs | 391 |
| r | 0.007885068502064396 |
| Best lag | -3 (days) |
| perm_p | 0.5868263473053892 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.7, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.usa.tone` (configured analysis window); `finance.DX-Y.NYB.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.007885068502064396, n=391).

The best tested lag was -3 days with r=0.10566829392591708.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long DX-Y**, hold 1d
- Entry: gdelt.usa.tone rolling_zscore_20d > 1 at close -> long DX-Y next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=50 hit_rate=0.42 avg_return=-0.0008004138320158383 excess=-0.0007148125324031888 sharpe_like=-1.2424769288767255 max_dd=-0.04541720256384485
- OOS (war period): n=17 hit=0.5882352941176471 avg=7.035009614909856e-05
- Actionability: 0.7
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
