# R2-0174

| Field | Value |
|---|---|
| Mission id | `R2-0174` |
| Folder | `20260920-265-finance-spread-gasoline-crack_x_finance-jets-log-return` |
| Indicators | `finance.spread.gasoline_crack` × `finance.JETS.log_return` |
| n_obs | 389 |
| r | 0.0532714993348745 |
| Best lag | -9 (days) |
| perm_p | 0.32934131736526945 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 6.92, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.spread.gasoline_crack` (configured analysis window); `finance.JETS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0532714993348745, n=389).

The best tested lag was -9 days with r=0.1329894236168762.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long JETS**, hold 1d
- Entry: finance.spread.gasoline_crack rolling_zscore_20d > 1 at close -> long JETS next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=48 hit_rate=0.4583333333333333 avg_return=0.003249298017918787 excess=0.0023375678802842422 sharpe_like=1.2496265727562235 max_dd=-0.07221331851848078
- OOS (war period): n=20 hit=0.45 avg=0.002488840761641453
- Actionability: 6.92
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
