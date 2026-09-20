# R2-0096

| Field | Value |
|---|---|
| Mission id | `R2-0096` |
| Folder | `20260920-197-finance-bz-f-log-return_x_finance-inda-log-return` |
| Indicators | `finance.BZ=F.log_return` × `finance.INDA.log_return` |
| n_obs | 390 |
| r | -0.3440143193707558 |
| Best lag | 0 (days) |
| perm_p | 0.015968063872255488 |
| Bonferroni | 0.1117764471057884 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 6.75, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.BZ=F.log_return` (configured analysis window); `finance.INDA.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.3440143193707558, n=390).

The best tested lag was 0 days with r=-0.344014319370756.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short INDA**, hold 1d
- Entry: finance.BZ=F.log_return rolling_zscore_20d > 1 at close -> short INDA next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=50 hit_rate=0.48 avg_return=0.0008184187144961386 excess=0.0008181486656328294 sharpe_like=0.6679930492271651 max_dd=-0.042097206335652726
- OOS (war period): n=16 hit=0.5 avg=0.00040265529629364416
- Actionability: 6.75
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
