# R2-0157

| Field | Value |
|---|---|
| Mission id | `R2-0157` |
| Folder | `20260920-252-finance-mos-close_x_finance-mos-log-return` |
| Indicators | `finance.MOS.close` × `finance.MOS.log_return` |
| n_obs | 389 |
| r | 0.9999999999999998 |
| Best lag | 0 (days) |
| perm_p | 0.041916167664670656 |
| Bonferroni | 0.8802395209580838 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 8.12, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.MOS.close` (configured analysis window); `finance.MOS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.9999999999999998, n=389).

The best tested lag was 0 days with r=1.0.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long MOS**, hold 1d
- Entry: finance.MOS.close rolling_zscore_20d > 1 at close -> long MOS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=41 hit_rate=0.5609756097560976 avg_return=0.007225940757063084 excess=0.0070714299988597715 sharpe_like=1.6273985831603268 max_dd=-0.07680008949349548
- OOS (war period): n=18 hit=0.6111111111111112 avg=0.013414525489342152
- Actionability: 8.12
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
