# R2-0036

| Field | Value |
|---|---|
| Mission id | `R2-0036` |
| Folder | `20260920-157-finance-ratio-ttf-henryhub_x_finance-lng-log-return` |
| Indicators | `finance.ratio.ttf_henryhub` × `finance.LNG.log_return` |
| n_obs | 389 |
| r | 0.13574652087465516 |
| Best lag | 0 (days) |
| perm_p | 0.17165668662674652 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 1.13, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.ratio.ttf_henryhub` (configured analysis window); `finance.LNG.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.13574652087465516, n=389).

The best tested lag was 0 days with r=0.13574652087465494.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long LNG**, hold 1d
- Entry: finance.ratio.ttf_henryhub rolling_zscore_20d > 1 at close -> long LNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=44 hit_rate=0.45454545454545453 avg_return=0.0003984304151261583 excess=-0.0002742968907394424 sharpe_like=0.1504207581511494 max_dd=-0.1458276085584379
- OOS (war period): n=15 hit=0.4 avg=-0.0027233914345018723
- Actionability: 1.13
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
