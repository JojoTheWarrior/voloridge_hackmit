# R2-0106

| Field | Value |
|---|---|
| Mission id | `R2-0106` |
| Folder | `20260920-204-gdelt-gkg-oil-share_x_finance-spread-brent-wti` |
| Indicators | `gdelt.gkg.oil_share` × `finance.spread.brent_wti` |
| n_obs | 390 |
| r | -0.003272040950603387 |
| Best lag | -4 (days) |
| perm_p | 0.3992015968063872 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.02, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.oil_share` (configured analysis window); `finance.spread.brent_wti` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.003272040950603387, n=390).

The best tested lag was -4 days with r=-0.05683021088178342.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short spread:brent_wti**, hold 1d
- Entry: gdelt.gkg.oil_share rolling_zscore_20d > 1 at close -> short spread:brent_wti next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=57 hit_rate=0.5614035087719298 avg_return=0.11315770734820449 excess=0.11398887538670896 sharpe_like=1.360768560158462 max_dd=-21.17063009334319
- OOS (war period): n=16 hit=0.6875 avg=0.2949991226196289
- Actionability: 7.02
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
