# R2-0041

| Field | Value |
|---|---|
| Mission id | `R2-0041` |
| Folder | `20260920-160-gdelt-gkg-lng-share_x_finance-cf-log-return` |
| Indicators | `gdelt.gkg.lng_share` × `finance.CF.log_return` |
| n_obs | 390 |
| r | 0.06847395908051869 |
| Best lag | 3 (days) |
| perm_p | 0.021956087824351298 |
| Bonferroni | 0.46107784431137727 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.77, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.lng_share` (configured analysis window); `finance.CF.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.06847395908051869, n=390).

The best tested lag was 3 days with r=0.16550244678293996.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 3d
- Entry: gdelt.gkg.lng_share rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=37 hit_rate=0.5945945945945946 avg_return=0.004928345321671503 excess=-0.00010178696830436245 sharpe_like=0.719953820623756 max_dd=-0.1426245843049998
- OOS (war period): n=13 hit=0.5384615384615384 avg=-0.0003024196135718881
- Actionability: 2.77
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
