# R2-0185

| Field | Value |
|---|---|
| Mission id | `R2-0185` |
| Folder | `20260920-271-research-lithium-crossref-pubs_x_finance-inda-log-return` |
| Indicators | `research.lithium.crossref_pubs` × `finance.INDA.log_return` |
| n_obs | 81 |
| r | 0.03827573113212109 |
| Best lag | 1 (weeks) |
| perm_p | 0.9760479041916168 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.29, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `research.lithium.crossref_pubs` (2025-03..current week); `finance.INDA.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.03827573113212109, n=81).

The best tested lag was 1 weeks with r=0.04738289678211935.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short INDA**, hold 1d
- Entry: research.lithium.crossref_pubs rolling_zscore_20d > 1 at close -> short INDA next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=7 hit_rate=0.7142857142857143 avg_return=0.0052892896426450465 excess=0.0039598114684728245 sharpe_like=1.550672959517235 max_dd=-0.0023280552455359205
- OOS (war period): n=4 hit=0.75 avg=0.006837561325353875
- Actionability: 8.29
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
