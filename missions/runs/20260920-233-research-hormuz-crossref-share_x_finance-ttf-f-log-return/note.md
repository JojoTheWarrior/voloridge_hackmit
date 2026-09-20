# R2-0131

| Field | Value |
|---|---|
| Mission id | `R2-0131` |
| Folder | `20260920-233-research-hormuz-crossref-share_x_finance-ttf-f-log-return` |
| Indicators | `research.hormuz.crossref_share` × `finance.TTF=F.log_return` |
| n_obs | 81 |
| r | 0.024053236493362797 |
| Best lag | 1 (weeks) |
| perm_p | 0.017964071856287425 |
| Bonferroni | 0.05389221556886227 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.58, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_share` (2025-03..current week); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.024053236493362797, n=81).

The best tested lag was 1 weeks with r=0.42525025565640945.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long TTF=F**, hold 1d
- Entry: research.hormuz.crossref_share rolling_zscore_20d > 1 at close -> long TTF=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=8 hit_rate=0.375 avg_return=-0.006538401262503879 excess=-0.0064387521718400524 sharpe_like=-0.784375542010758 max_dd=-0.08679834083028026
- OOS (war period): n=2 hit=0.5 avg=0.0021493261566613575
- Actionability: 0.58
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
