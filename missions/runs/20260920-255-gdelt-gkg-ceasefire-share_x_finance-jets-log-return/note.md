# R2-0159

| Field | Value |
|---|---|
| Mission id | `R2-0159` |
| Folder | `20260920-255-gdelt-gkg-ceasefire-share_x_finance-jets-log-return` |
| Indicators | `gdelt.gkg.ceasefire_share` × `finance.JETS.log_return` |
| n_obs | 390 |
| r | 0.06340156284685255 |
| Best lag | -3 (days) |
| perm_p | 0.1656686626746507 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.04, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.ceasefire_share` (configured analysis window); `finance.JETS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.06340156284685255, n=390).

The best tested lag was -3 days with r=0.12839903997573104.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long JETS**, hold 1d
- Entry: gdelt.gkg.ceasefire_share rolling_zscore_20d > 1 at close -> long JETS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=29 hit_rate=0.5172413793103449 avg_return=0.003189725860780858 excess=0.002275458910221693 sharpe_like=1.0478383179811994 max_dd=-0.06304806598690538
- OOS (war period): n=14 hit=0.2857142857142857 avg=-0.0008318504897657905
- Actionability: 4.04
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
