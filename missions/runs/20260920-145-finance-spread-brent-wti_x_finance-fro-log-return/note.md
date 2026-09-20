# R2-0019

| Field | Value |
|---|---|
| Mission id | `R2-0019` |
| Folder | `20260920-145-finance-spread-brent-wti_x_finance-fro-log-return` |
| Indicators | `finance.spread.brent_wti` × `finance.FRO.log_return` |
| n_obs | 389 |
| r | 0.09648676406930573 |
| Best lag | 5 (days) |
| perm_p | 0.48303393213572854 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 1.44, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.spread.brent_wti` (configured analysis window); `finance.FRO.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.09648676406930573, n=389).

The best tested lag was 5 days with r=0.10780540176030118.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long FRO**, hold 5d
- Entry: finance.spread.brent_wti rolling_zscore_20d > 1 at close -> long FRO next session
- Exit: close after 5 trading days (no overlapping entries)
- n_trades=22 hit_rate=0.5909090909090909 avg_return=0.014255411012384563 excess=-0.00340245093694941 sharpe_like=0.8417570889153232 max_dd=-0.24003165776674773
- OOS (war period): n=10 hit=0.7 avg=0.0018317400545358575
- Actionability: 1.44
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
