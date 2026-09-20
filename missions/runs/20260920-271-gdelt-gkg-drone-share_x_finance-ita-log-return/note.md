# R2-0184

| Field | Value |
|---|---|
| Mission id | `R2-0184` |
| Folder | `20260920-271-gdelt-gkg-drone-share_x_finance-ita-log-return` |
| Indicators | `gdelt.gkg.drone_share` × `finance.ITA.log_return` |
| n_obs | 390 |
| r | -0.04894795192578041 |
| Best lag | 7 (days) |
| perm_p | 0.2375249500998004 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.drone_share` (configured analysis window); `finance.ITA.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.04894795192578041, n=390).

The best tested lag was 7 days with r=-0.1296407692453055.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ITA**, hold 7d
- Entry: gdelt.gkg.drone_share rolling_zscore_20d > 1 at close -> short ITA next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=17 hit_rate=0.23529411764705882 avg_return=-0.021262103943961472 excess=-0.013789382103775998 sharpe_like=-2.793621177814907 max_dd=-0.31056692625855586
- OOS (war period): n=4 hit=0.25 avg=-0.00995725168488723
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
