# R2-0032

| Field | Value |
|---|---|
| Mission id | `R2-0032` |
| Folder | `20260920-155-finance-ng-f-close_x_finance-xlu-log-return` |
| Indicators | `finance.NG=F.close` × `finance.XLU.log_return` |
| n_obs | 389 |
| r | 0.037738214374293644 |
| Best lag | 1 (days) |
| perm_p | 0.8203592814371258 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 3.1, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.NG=F.close` (configured analysis window); `finance.XLU.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.037738214374293644, n=389).

The best tested lag was 1 days with r=-0.0836888465193074.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short XLU**, hold 1d
- Entry: finance.NG=F.close rolling_zscore_20d > 1 at close -> short XLU next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=42 hit_rate=0.42857142857142855 avg_return=0.0008150036753290671 excess=0.000962234954134482 sharpe_like=0.5520059721301899 max_dd=-0.06355282980427635
- OOS (war period): n=15 hit=0.4 avg=-0.0007077280888627542
- Actionability: 3.1
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
