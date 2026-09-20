# R2-0179

| Field | Value |
|---|---|
| Mission id | `R2-0179` |
| Folder | `20260920-267-gdelt-irn-goldstein_x_finance-ita-log-return` |
| Indicators | `gdelt.irn.goldstein` × `finance.ITA.log_return` |
| n_obs | 390 |
| r | 0.1102507015965809 |
| Best lag | 0 (days) |
| perm_p | 0.4171656686626746 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.goldstein` (configured analysis window); `finance.ITA.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.1102507015965809, n=390).

The best tested lag was 0 days with r=0.11025070159658086.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ITA**, hold 1d
- Entry: gdelt.irn.goldstein rolling_zscore_20d > 1 at close -> short ITA next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=0.37037037037037035 avg_return=-0.004475165369152995 excess=-0.0034087582343459823 sharpe_like=-2.1073264911773757 max_dd=-0.23411809312380516
- OOS (war period): n=18 hit=0.4444444444444444 avg=-0.0009003884673444028
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
