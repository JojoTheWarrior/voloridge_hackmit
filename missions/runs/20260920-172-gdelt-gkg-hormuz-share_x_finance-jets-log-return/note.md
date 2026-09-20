# R2-0058

| Field | Value |
|---|---|
| Mission id | `R2-0058` |
| Folder | `20260920-172-gdelt-gkg-hormuz-share_x_finance-jets-log-return` |
| Indicators | `gdelt.gkg.hormuz_share` × `finance.JETS.log_return` |
| n_obs | 390 |
| r | -0.07139132444939622 |
| Best lag | 7 (days) |
| perm_p | 0.18762475049900199 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.2, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.hormuz_share` (configured analysis window); `finance.JETS.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.07139132444939622, n=390).

The best tested lag was 7 days with r=0.1439674054343664.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short JETS**, hold 7d
- Entry: gdelt.gkg.hormuz_share rolling_zscore_20d > 1 at close -> short JETS next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=3 hit_rate=0.6666666666666666 avg_return=0.009104630401223335 excess=0.02565956955845435 sharpe_like=0.8465237259011169 max_dd=0.0
- OOS (war period): n=3 hit=0.6666666666666666 avg=0.009104630401223335
- Actionability: 1.2
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
