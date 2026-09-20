# R2-0143

| Field | Value |
|---|---|
| Mission id | `R2-0143` |
| Folder | `20260920-242-gdelt-irn-conflict-events_x_finance-mos-abs-return` |
| Indicators | `gdelt.irn.conflict_events` × `finance.MOS.abs_return` |
| n_obs | 390 |
| r | 0.20657672747210698 |
| Best lag | 7 (days) |
| perm_p | 0.027944111776447105 |
| Bonferroni | 0.5868263473053892 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 10.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.conflict_events` (configured analysis window); `finance.MOS.abs_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.20657672747210698, n=390).

The best tested lag was 7 days with r=0.30511154887353176.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long MOS**, hold 7d
- Entry: gdelt.irn.conflict_events rolling_zscore_20d > 1 at close -> long MOS next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=26 hit_rate=1.0 avg_return=0.15656037600359993 excess=0.009469751132846399 sharpe_like=12.98192217947284 max_dd=0.0
- OOS (war period): n=8 hit=1.0 avg=0.17960105083707126
- Actionability: 10.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
