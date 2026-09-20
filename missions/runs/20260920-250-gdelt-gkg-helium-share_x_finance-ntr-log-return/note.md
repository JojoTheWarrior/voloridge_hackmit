# R2-0154

| Field | Value |
|---|---|
| Mission id | `R2-0154` |
| Folder | `20260920-250-gdelt-gkg-helium-share_x_finance-ntr-log-return` |
| Indicators | `gdelt.gkg.helium_share` × `finance.NTR.log_return` |
| n_obs | 390 |
| r | 0.08468332809613766 |
| Best lag | -1 (days) |
| perm_p | 0.05389221556886228 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.39, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.helium_share` (configured analysis window); `finance.NTR.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.08468332809613766, n=390).

The best tested lag was -1 days with r=0.18800760095071622.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short NTR**, hold 1d
- Entry: gdelt.gkg.helium_share rolling_zscore_20d > 1 at close -> short NTR next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=5 hit_rate=0.8 avg_return=0.009465587238669549 excess=0.011208378401238504 sharpe_like=2.678805252495255 max_dd=-0.001281451425158675
- OOS (war period): n=1 hit=1.0 avg=0.012985512694570489
- Actionability: 7.39
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
