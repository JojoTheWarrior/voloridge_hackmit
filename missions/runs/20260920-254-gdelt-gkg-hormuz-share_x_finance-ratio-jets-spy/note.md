# R2-0158

| Field | Value |
|---|---|
| Mission id | `R2-0158` |
| Folder | `20260920-254-gdelt-gkg-hormuz-share_x_finance-ratio-jets-spy` |
| Indicators | `gdelt.gkg.hormuz_share` × `finance.ratio.jets_spy` |
| n_obs | 389 |
| r | -0.04953099511963074 |
| Best lag | 7 (days) |
| perm_p | 0.6207584830339321 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.2, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.hormuz_share` (configured analysis window); `finance.ratio.jets_spy` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.04953099511963074, n=389).

The best tested lag was 7 days with r=0.1090225979909589.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ratio:jets_spy**, hold 7d
- Entry: gdelt.gkg.hormuz_share rolling_zscore_20d > 1 at close -> short ratio:jets_spy next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=3 hit_rate=0.3333333333333333 avg_return=0.0053616033340690246 excess=0.003345626744459639 sharpe_like=0.4170641437097111 max_dd=-0.006634477853403764
- OOS (war period): n=3 hit=0.3333333333333333 avg=0.0053616033340690246
- Actionability: 1.2
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
