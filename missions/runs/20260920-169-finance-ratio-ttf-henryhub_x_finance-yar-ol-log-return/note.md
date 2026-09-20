# R2-0055

| Field | Value |
|---|---|
| Mission id | `R2-0055` |
| Folder | `20260920-169-finance-ratio-ttf-henryhub_x_finance-yar-ol-log-return` |
| Indicators | `finance.ratio.ttf_henryhub` × `finance.YAR.OL.log_return` |
| n_obs | 376 |
| r | 0.12606694963624568 |
| Best lag | 0 (days) |
| perm_p | 0.47704590818363274 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.42, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.ratio.ttf_henryhub` (configured analysis window); `finance.YAR.OL.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.12606694963624568, n=376).

The best tested lag was 0 days with r=0.12606694963624568.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short YAR**, hold 1d
- Entry: finance.ratio.ttf_henryhub rolling_zscore_20d > 1 at close -> short YAR next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=43 hit_rate=0.3953488372093023 avg_return=-0.002324770555662696 excess=-0.0012455336570743572 sharpe_like=-0.8701610344484615 max_dd=-0.148429651827913
- OOS (war period): n=15 hit=0.26666666666666666 avg=-0.007473521704739449
- Actionability: 0.42
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
