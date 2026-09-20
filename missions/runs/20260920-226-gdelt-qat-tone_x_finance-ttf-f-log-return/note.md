# R2-0121

| Field | Value |
|---|---|
| Mission id | `R2-0121` |
| Folder | `20260920-226-gdelt-qat-tone_x_finance-ttf-f-log-return` |
| Indicators | `gdelt.qat.tone` × `finance.TTF=F.log_return` |
| n_obs | 391 |
| r | -0.10259015335606719 |
| Best lag | 0 (days) |
| perm_p | 0.4291417165668663 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.qat.tone` (configured analysis window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.10259015335606719, n=391).

The best tested lag was 0 days with r=-0.10259015335606712.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short TTF=F**, hold 1d
- Entry: gdelt.qat.tone rolling_zscore_20d > 1 at close -> short TTF=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=51 hit_rate=0.3333333333333333 avg_return=-0.007261832059513974 excess=-0.004725439972710073 sharpe_like=-1.5397357561147316 max_dd=-0.36938514279351686
- OOS (war period): n=18 hit=0.2777777777777778 avg=-0.009249830437709716
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
