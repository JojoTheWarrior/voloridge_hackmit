# R2-0176

| Field | Value |
|---|---|
| Mission id | `R2-0176` |
| Folder | `20260920-265-finance-vix-log-return_x_finance-fdx-log-return` |
| Indicators | `finance.^VIX.log_return` × `finance.FDX.log_return` |
| n_obs | 390 |
| r | -0.48126450023555806 |
| Best lag | 0 (days) |
| perm_p | 0.003992015968063872 |
| Bonferroni | 0.0279441117764471 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 1.77, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.^VIX.log_return` (configured analysis window); `finance.FDX.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.48126450023555806, n=390).

The best tested lag was 0 days with r=-0.4812645002355584.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long FDX**, hold 1d
- Entry: finance.^VIX.log_return rolling_zscore_20d > 1 at close -> long FDX next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=51 hit_rate=0.5098039215686274 avg_return=0.0006855121813921402 excess=-0.0006806625959625759 sharpe_like=0.2528401799623833 max_dd=-0.08120644217700457
- OOS (war period): n=23 hit=0.30434782608695654 avg=-0.002033733200156593
- Actionability: 1.77
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
