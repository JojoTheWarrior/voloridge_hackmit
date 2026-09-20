# R2-0175

| Field | Value |
|---|---|
| Mission id | `R2-0175` |
| Folder | `20260920-265-finance-bz-f-log-return_x_finance-ccl-log-return` |
| Indicators | `finance.BZ=F.log_return` × `finance.CCL.log_return` |
| n_obs | 390 |
| r | -0.2976823935060568 |
| Best lag | 0 (days) |
| perm_p | 0.017964071856287425 |
| Bonferroni | 0.12574850299401197 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 6.32, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.BZ=F.log_return` (configured analysis window); `finance.CCL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.2976823935060568, n=390).

The best tested lag was 0 days with r=-0.29768239350605685.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short CCL**, hold 1d
- Entry: finance.BZ=F.log_return rolling_zscore_20d > 1 at close -> short CCL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=50 hit_rate=0.52 avg_return=0.0037427483462088972 excess=0.004456015357583186 sharpe_like=0.9357596741512346 max_dd=-0.18564798942005933
- OOS (war period): n=16 hit=0.625 avg=0.004328881805663237
- Actionability: 6.32
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
