# R2-0173

| Field | Value |
|---|---|
| Mission id | `R2-0173` |
| Folder | `20260920-264-finance-spread-gasoline-crack_x_finance-ratio-jets-spy` |
| Indicators | `finance.spread.gasoline_crack` × `finance.ratio.jets_spy` |
| n_obs | 389 |
| r | 0.03683000400928406 |
| Best lag | -6 (days) |
| perm_p | 0.023952095808383235 |
| Bonferroni | 0.502994011976048 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.5, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.spread.gasoline_crack` (configured analysis window); `finance.ratio.jets_spy` (configured analysis window) |

**Verdict:** supported (Pearson r=0.03683000400928406, n=389).

The best tested lag was -6 days with r=-0.15834065390869898.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ratio:jets_spy**, hold 1d
- Entry: finance.spread.gasoline_crack rolling_zscore_20d > 1 at close -> short ratio:jets_spy next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=48 hit_rate=0.5 avg_return=-0.0020081198251989513 excess=-0.001996253144342273 sharpe_like=-0.8971394426090874 max_dd=-0.15207665826696004
- OOS (war period): n=20 hit=0.55 avg=-0.001083682873591274
- Actionability: 0.5
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
