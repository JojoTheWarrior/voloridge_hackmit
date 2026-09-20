# R2-0074

| Field | Value |
|---|---|
| Mission id | `R2-0074` |
| Folder | `20260920-183-finance-spread-gasoline-crack_x_finance-jets-log-return` |
| Indicators | `finance.spread.gasoline_crack` × `finance.JETS.log_return` |
| n_obs | 389 |
| r | 0.0532714993348745 |
| Best lag | 5 (days) |
| perm_p | 0.7385229540918163 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 3.99, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.spread.gasoline_crack` (configured analysis window); `finance.JETS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0532714993348745, n=389).

The best tested lag was 5 days with r=0.08488379113124205.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long JETS**, hold 5d
- Entry: finance.spread.gasoline_crack rolling_zscore_20d > 1 at close -> long JETS next session
- Exit: close after 5 trading days (no overlapping entries)
- n_trades=31 hit_rate=0.5483870967741935 avg_return=0.003799233063145611 excess=-0.0005455015088659393 sharpe_like=0.4395410268728095 max_dd=-0.15199710402655997
- OOS (war period): n=11 hit=0.5454545454545454 avg=0.009505481267096928
- Actionability: 3.99
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
