# R2-0017

| Field | Value |
|---|---|
| Mission id | `R2-0017` |
| Folder | `20260920-146-research-hormuz-crossref-pubs_x_finance-xop-log-return` |
| Indicators | `research.hormuz.crossref_pubs` × `finance.XOP.log_return` |
| n_obs | 81 |
| r | 0.053176529884105546 |
| Best lag | 1 (weeks) |
| perm_p | 0.4151696606786427 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.hormuz.crossref_pubs` (2025-03..current week); `finance.XOP.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.053176529884105546, n=81).

The best tested lag was 1 weeks with r=0.13172665105778197.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short XOP**, hold 1d
- Entry: research.hormuz.crossref_pubs rolling_zscore_20d > 1 at close -> short XOP next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=7 hit_rate=0.2857142857142857 avg_return=-0.006826225233780673 excess=-0.0034229954094274918 sharpe_like=-2.0631324356484937 max_dd=-0.03948701662995269
- OOS (war period): n=2 hit=0.0 avg=-0.012868138874732482
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
