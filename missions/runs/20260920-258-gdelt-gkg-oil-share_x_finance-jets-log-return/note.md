# R2-0166

| Field | Value |
|---|---|
| Mission id | `R2-0166` |
| Folder | `20260920-258-gdelt-gkg-oil-share_x_finance-jets-log-return` |
| Indicators | `gdelt.gkg.oil_share` × `finance.JETS.log_return` |
| n_obs | 390 |
| r | -0.00032887920011135524 |
| Best lag | -7 (days) |
| perm_p | 0.654690618762475 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.59, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.oil_share` (configured analysis window); `finance.JETS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.00032887920011135524, n=390).

The best tested lag was -7 days with r=-0.06142708549816759.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short JETS**, hold 1d
- Entry: gdelt.gkg.oil_share rolling_zscore_20d > 1 at close -> short JETS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=57 hit_rate=0.5087719298245614 avg_return=-0.0015555053702462206 excess=-0.0006412384196870553 sharpe_like=-0.6515270747442072 max_dd=-0.21106554992982318
- OOS (war period): n=16 hit=0.5625 avg=0.0009851233866279632
- Actionability: 3.59
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
