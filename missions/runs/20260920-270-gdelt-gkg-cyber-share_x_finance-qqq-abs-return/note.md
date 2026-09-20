# R2-0183

| Field | Value |
|---|---|
| Mission id | `R2-0183` |
| Folder | `20260920-270-gdelt-gkg-cyber-share_x_finance-qqq-abs-return` |
| Indicators | `gdelt.gkg.cyber_share` × `finance.QQQ.abs_return` |
| n_obs | 390 |
| r | 0.020634513767522553 |
| Best lag | 10 (days) |
| perm_p | 0.469061876247505 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.03, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.cyber_share` (configured analysis window); `finance.QQQ.abs_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.020634513767522553, n=390).

The best tested lag was 10 days with r=0.13032368381213608.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long QQQ**, hold 10d
- Entry: gdelt.gkg.cyber_share rolling_zscore_20d > 1 at close -> long QQQ next session
- Exit: close after 10 trading days (no overlapping entries)
- n_trades=24 hit_rate=1.0 avg_return=0.10400136802330855 excess=0.0025727641529182665 sharpe_like=8.355731139588244 max_dd=0.0
- OOS (war period): n=8 hit=1.0 avg=0.10995285281281128
- Actionability: 7.03
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
