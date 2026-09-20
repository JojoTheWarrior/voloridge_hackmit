# R2-0178

| Field | Value |
|---|---|
| Mission id | `R2-0178` |
| Folder | `20260920-266-gdelt-gkg-sanctions-share_x_finance-gld-log-return` |
| Indicators | `gdelt.gkg.sanctions_share` × `finance.GLD.log_return` |
| n_obs | 390 |
| r | -0.08306755051088213 |
| Best lag | -6 (days) |
| perm_p | 0.562874251497006 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.45, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.sanctions_share` (configured analysis window); `finance.GLD.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.08306755051088213, n=390).

The best tested lag was -6 days with r=-0.08868468468751378.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long GLD**, hold 1d
- Entry: gdelt.gkg.sanctions_share rolling_zscore_20d > 1 at close -> long GLD next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=42 hit_rate=0.5 avg_return=-0.0029603635371573136 excess=-0.004169164006234729 sharpe_like=-1.118647817956665 max_dd=-0.1352120873848427
- OOS (war period): n=12 hit=0.5 avg=-0.007258787114806958
- Actionability: 1.45
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
