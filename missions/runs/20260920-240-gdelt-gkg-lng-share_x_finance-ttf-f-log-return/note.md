# R2-0139

| Field | Value |
|---|---|
| Mission id | `R2-0139` |
| Folder | `20260920-240-gdelt-gkg-lng-share_x_finance-ttf-f-log-return` |
| Indicators | `gdelt.gkg.lng_share` × `finance.TTF=F.log_return` |
| n_obs | 391 |
| r | 0.24710120456775034 |
| Best lag | 0 (days) |
| perm_p | 0.033932135728542916 |
| Bonferroni | 0.7125748502994013 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.31, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.lng_share` (configured analysis window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.24710120456775034, n=391).

The best tested lag was 0 days with r=0.24710120456775056.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long TTF=F**, hold 1d
- Entry: gdelt.gkg.lng_share rolling_zscore_20d > 1 at close -> long TTF=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=51 hit_rate=0.47058823529411764 avg_return=0.0010693949433450362 excess=-0.0014669971434588648 sharpe_like=0.15799326195881735 max_dd=-0.19374756864824538
- OOS (war period): n=15 hit=0.5333333333333333 avg=0.015359903583319194
- Actionability: 3.31
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
