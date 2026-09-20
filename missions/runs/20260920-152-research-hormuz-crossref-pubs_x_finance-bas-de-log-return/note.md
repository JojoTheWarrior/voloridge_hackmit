# R2-0030

| Field | Value |
|---|---|
| Mission id | `R2-0030` |
| Folder | `20260920-152-research-hormuz-crossref-pubs_x_finance-bas-de-log-return` |
| Indicators | `research.hormuz.crossref_pubs` × `finance.BAS.DE.log_return` |
| n_obs | 81 |
| r | 0.04614965606202643 |
| Best lag | 0 (weeks) |
| perm_p | 0.5748502994011976 |
| Bonferroni | 0.5748502994011976 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_pubs` (2025-03..current week); `finance.BAS.DE.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.04614965606202643, n=81).

The best tested lag was 0 weeks with r=0.04614965606202642.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short BAS**, hold 1d
- Entry: research.hormuz.crossref_pubs rolling_zscore_20d > 1 at close -> short BAS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=8 hit_rate=0.25 avg_return=-0.004063867586019523 excess=-0.001864817979603607 sharpe_like=-0.6746511387658757 max_dd=-0.05165439194568666
- OOS (war period): n=2 hit=0.0 avg=-0.0027338629011522952
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
