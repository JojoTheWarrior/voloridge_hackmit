# R2-0076

| Field | Value |
|---|---|
| Mission id | `R2-0076` |
| Folder | `20260920-184-finance-vix-close_x_finance-fdx-log-return` |
| Indicators | `finance.^VIX.close` × `finance.FDX.log_return` |
| n_obs | 389 |
| r | -0.47984187429127634 |
| Best lag | 0 (days) |
| perm_p | 0.013972055888223553 |
| Bonferroni | 0.09780439121756487 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 5.4, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.^VIX.close` (configured analysis window); `finance.FDX.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.47984187429127634, n=389).

The best tested lag was 0 days with r=-0.47984187429127634.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short FDX**, hold 1d
- Entry: finance.^VIX.close rolling_zscore_20d > 1 at close -> short FDX next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=51 hit_rate=0.49019607843137253 avg_return=-0.0006855121813921402 excess=0.000650495930459626 sharpe_like=-0.2528401799623833 max_dd=-0.17001127848182185
- OOS (war period): n=23 hit=0.6956521739130435 avg=0.002033733200156593
- Actionability: 5.4
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
