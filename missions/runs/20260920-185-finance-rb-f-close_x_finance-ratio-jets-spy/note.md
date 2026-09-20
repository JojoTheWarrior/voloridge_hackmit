# R2-0077

| Field | Value |
|---|---|
| Mission id | `R2-0077` |
| Folder | `20260920-185-finance-rb-f-close_x_finance-ratio-jets-spy` |
| Indicators | `finance.RB=F.close` × `finance.ratio.jets_spy` |
| n_obs | 389 |
| r | -0.33632320585918696 |
| Best lag | 0 (days) |
| perm_p | 0.03592814371257485 |
| Bonferroni | 0.7544910179640718 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 4.34, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.RB=F.close` (configured analysis window); `finance.ratio.jets_spy` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.33632320585918696, n=389).

The best tested lag was 0 days with r=-0.33632320585918696.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ratio:jets_spy**, hold 1d
- Entry: finance.RB=F.close rolling_zscore_20d > 1 at close -> short ratio:jets_spy next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=49 hit_rate=0.5510204081632653 avg_return=0.0011198125528971816 excess=0.0011316792337538598 sharpe_like=0.4997752935009508 max_dd=-0.07240930554746461
- OOS (war period): n=17 hit=0.5294117647058824 avg=-0.0018215672332574113
- Actionability: 4.34
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
