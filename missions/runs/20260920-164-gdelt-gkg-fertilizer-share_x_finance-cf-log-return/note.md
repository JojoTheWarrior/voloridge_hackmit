# R2-0046

| Field | Value |
|---|---|
| Mission id | `R2-0046` |
| Folder | `20260920-164-gdelt-gkg-fertilizer-share_x_finance-cf-log-return` |
| Indicators | `gdelt.gkg.fertilizer_share` × `finance.CF.log_return` |
| n_obs | 390 |
| r | -0.06488065741584294 |
| Best lag | 8 (days) |
| perm_p | 0.32335329341317365 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.9, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.fertilizer_share` (configured analysis window); `finance.CF.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.06488065741584294, n=390).

The best tested lag was 8 days with r=-0.09624670992498377.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short CF**, hold 8d
- Entry: gdelt.gkg.fertilizer_share rolling_zscore_20d > 1 at close -> short CF next session
- Exit: close after 8 trading days (no overlapping entries)
- n_trades=20 hit_rate=0.5 avg_return=-0.00282622597231062 excess=0.010850773900403815 sharpe_like=-0.21167190668968258 max_dd=-0.2812241618215017
- OOS (war period): n=9 hit=0.5555555555555556 avg=-0.012319597324175091
- Actionability: 4.9
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
