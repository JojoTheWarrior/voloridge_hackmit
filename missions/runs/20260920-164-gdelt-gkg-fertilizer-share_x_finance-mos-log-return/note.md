# R2-0047

| Field | Value |
|---|---|
| Mission id | `R2-0047` |
| Folder | `20260920-164-gdelt-gkg-fertilizer-share_x_finance-mos-log-return` |
| Indicators | `gdelt.gkg.fertilizer_share` × `finance.MOS.log_return` |
| n_obs | 390 |
| r | -0.09550171460422124 |
| Best lag | 0 (days) |
| perm_p | 0.4471057884231537 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.fertilizer_share` (configured analysis window); `finance.MOS.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.09550171460422124, n=390).

The best tested lag was 0 days with r=-0.09550171460422129.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long MOS**, hold 1d
- Entry: gdelt.gkg.fertilizer_share rolling_zscore_20d > 1 at close -> long MOS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=45 hit_rate=0.4 avg_return=-0.010388810600661928 excess=-0.010711068897947599 sharpe_like=-1.8731661391105945 max_dd=-0.39361870826884426
- OOS (war period): n=20 hit=0.4 avg=-0.007367496338657293
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
