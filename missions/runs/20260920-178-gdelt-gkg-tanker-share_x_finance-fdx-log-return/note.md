# R2-0066

| Field | Value |
|---|---|
| Mission id | `R2-0066` |
| Folder | `20260920-178-gdelt-gkg-tanker-share_x_finance-fdx-log-return` |
| Indicators | `gdelt.gkg.tanker_share` × `finance.FDX.log_return` |
| n_obs | 390 |
| r | -0.06934868232571795 |
| Best lag | 0 (days) |
| perm_p | 0.9001996007984032 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.07, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.tanker_share` (configured analysis window); `finance.FDX.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.06934868232571795, n=390).

The best tested lag was 0 days with r=-0.06934868232571795.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short FDX**, hold 1d
- Entry: gdelt.gkg.tanker_share rolling_zscore_20d > 1 at close -> short FDX next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=28 hit_rate=0.39285714285714285 avg_return=-0.005372258390542934 excess=-0.004065794692119475 sharpe_like=-1.6944875700847641 max_dd=-0.16438281166624413
- OOS (war period): n=11 hit=0.6363636363636364 avg=0.0024546016481449173
- Actionability: 2.07
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
