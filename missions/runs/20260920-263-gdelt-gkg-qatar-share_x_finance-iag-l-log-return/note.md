# R2-0171

| Field | Value |
|---|---|
| Mission id | `R2-0171` |
| Folder | `20260920-263-gdelt-gkg-qatar-share_x_finance-iag-l-log-return` |
| Indicators | `gdelt.gkg.qatar_share` × `finance.IAG.L.log_return` |
| n_obs | 390 |
| r | -0.05582498750036028 |
| Best lag | 8 (days) |
| perm_p | 0.4810379241516966 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.qatar_share` (configured analysis window); `finance.IAG.L.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.05582498750036028, n=390).

The best tested lag was 8 days with r=-0.10131113702845254.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short IAG**, hold 8d
- Entry: gdelt.gkg.qatar_share rolling_zscore_20d > 1 at close -> short IAG next session
- Exit: close after 8 trading days (no overlapping entries)
- n_trades=20 hit_rate=0.3 avg_return=-0.03472410109596897 excess=-0.024981174702593433 sharpe_like=-2.5121929856228715 max_dd=-0.5049984224952925
- OOS (war period): n=4 hit=0.25 avg=-0.030624364651904212
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
