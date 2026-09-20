# R2-0182

| Field | Value |
|---|---|
| Mission id | `R2-0182` |
| Folder | `20260920-269-finance-dx-y-nyb-log-return_x_gdelt-usa-tone` |
| Indicators | `finance.DX-Y.NYB.log_return` × `gdelt.usa.tone` |
| n_obs | 391 |
| r | 0.007885068502064399 |
| Best lag | 3 (days) |
| perm_p | 0.2654690618762475 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.35, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.DX-Y.NYB.log_return` (configured analysis window); `gdelt.usa.tone` (configured analysis window) |

**Verdict:** supported (Pearson r=0.007885068502064399, n=391).

The best tested lag was 3 days with r=0.10566829392591708.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long gdelt.usa.tone**, hold 3d
- Entry: finance.DX-Y.NYB.log_return rolling_zscore_20d > 1 at close -> long gdelt.usa.tone next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=37 hit_rate=0.0 avg_return=-2.5926823030684507 excess=0.09236600462750477 sharpe_like=-19.475896411111368 max_dd=-4.963715752348429
- OOS (war period): n=13 hit=0.0 avg=-2.5123276223693227
- Actionability: 3.35
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
