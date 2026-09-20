# R2-0189

| Field | Value |
|---|---|
| Mission id | `R2-0189` |
| Folder | `20260920-274-gdelt-gkg-sanctions-share_x_finance-tur-log-return` |
| Indicators | `gdelt.gkg.sanctions_share` × `finance.TUR.log_return` |
| n_obs | 390 |
| r | 0.0292567422280184 |
| Best lag | -4 (days) |
| perm_p | 0.34530938123752497 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.73, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.sanctions_share` (configured analysis window); `finance.TUR.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.0292567422280184, n=390).

The best tested lag was -4 days with r=0.10555581168868232.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short TUR**, hold 1d
- Entry: gdelt.gkg.sanctions_share rolling_zscore_20d > 1 at close -> short TUR next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=42 hit_rate=0.42857142857142855 avg_return=-0.002125496872952683 excess=-0.0019411465965858148 sharpe_like=-1.070889687749325 max_dd=-0.09636720511111097
- OOS (war period): n=12 hit=0.4166666666666667 avg=-0.0019405124457237226
- Actionability: 0.73
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
