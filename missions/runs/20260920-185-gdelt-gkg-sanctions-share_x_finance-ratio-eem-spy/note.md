# R2-0078

| Field | Value |
|---|---|
| Mission id | `R2-0078` |
| Folder | `20260920-185-gdelt-gkg-sanctions-share_x_finance-ratio-eem-spy` |
| Indicators | `gdelt.gkg.sanctions_share` × `finance.ratio.eem_spy` |
| n_obs | 389 |
| r | 0.0025622726746149095 |
| Best lag | -10 (days) |
| perm_p | 0.7425149700598802 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.21, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.sanctions_share` (configured analysis window); `finance.ratio.eem_spy` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0025622726746149095, n=389).

The best tested lag was -10 days with r=-0.08318797446174224.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ratio:eem_spy**, hold 1d
- Entry: gdelt.gkg.sanctions_share rolling_zscore_20d > 1 at close -> short ratio:eem_spy next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=42 hit_rate=0.47619047619047616 avg_return=-0.0005782963147814515 excess=-0.00018811050883896886 sharpe_like=-0.35509268363507357 max_dd=-0.06710153195051005
- OOS (war period): n=12 hit=0.5 avg=-0.0017051956405802204
- Actionability: 1.21
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
