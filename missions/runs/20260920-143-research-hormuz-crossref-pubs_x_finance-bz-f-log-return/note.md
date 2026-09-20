# R2-0016

| Field | Value |
|---|---|
| Mission id | `R2-0016` |
| Folder | `20260920-143-research-hormuz-crossref-pubs_x_finance-bz-f-log-return` |
| Indicators | `research.hormuz.crossref_pubs` × `finance.BZ=F.log_return` |
| n_obs | 81 |
| r | 0.1021135859521833 |
| Best lag | 1 (weeks) |
| perm_p | 0.06187624750499002 |
| Bonferroni | 0.18562874251497005 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.05, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_pubs` (2025-03..current week); `finance.BZ=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.1021135859521833, n=81).

The best tested lag was 1 weeks with r=0.32406688574811066.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short BZ=F**, hold 1d
- Entry: research.hormuz.crossref_pubs rolling_zscore_20d > 1 at close -> short BZ=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=7 hit_rate=0.42857142857142855 avg_return=-0.008892383367314016 excess=-0.008857091788112764 sharpe_like=-1.080020043955657 max_dd=-0.09139759093708033
- OOS (war period): n=2 hit=0.0 avg=-0.028355519700508314
- Actionability: 1.05
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
