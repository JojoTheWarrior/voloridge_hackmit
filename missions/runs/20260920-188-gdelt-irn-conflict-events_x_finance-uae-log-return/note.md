# R2-0081

| Field | Value |
|---|---|
| Mission id | `R2-0081` |
| Folder | `20260920-188-gdelt-irn-conflict-events_x_finance-uae-log-return` |
| Indicators | `gdelt.irn.conflict_events` × `finance.UAE.log_return` |
| n_obs | 390 |
| r | -0.1776171763743212 |
| Best lag | -1 (days) |
| perm_p | 0.05389221556886228 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.18, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.conflict_events` (configured analysis window); `finance.UAE.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.1776171763743212, n=390).

The best tested lag was -1 days with r=-0.1782303761830324.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short UAE**, hold 1d
- Entry: gdelt.irn.conflict_events rolling_zscore_20d > 1 at close -> short UAE next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=62 hit_rate=0.46774193548387094 avg_return=-0.0003680703243289883 excess=0.00020123626542843664 sharpe_like=-0.2172637922639712 max_dd=-0.09287571231622926
- OOS (war period): n=21 hit=0.5714285714285714 avg=0.0031731995297474254
- Actionability: 6.18
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
