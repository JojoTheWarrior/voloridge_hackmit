# R2-0008

| Field | Value |
|---|---|
| Mission id | `R2-0008` |
| Folder | `20260920-138-gdelt-gkg-sanctions-share_x_finance-spread-gasoline-crack` |
| Indicators | `gdelt.gkg.sanctions_share` × `finance.spread.gasoline_crack` |
| n_obs | 390 |
| r | 0.06194677781276006 |
| Best lag | 6 (days) |
| perm_p | 0.48902195608782434 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.96, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.sanctions_share` (configured analysis window); `finance.spread.gasoline_crack` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.06194677781276006, n=390).

The best tested lag was 6 days with r=-0.10279827746244777.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long spread:gasoline_crack**, hold 6d
- Entry: gdelt.gkg.sanctions_share rolling_zscore_20d > 1 at close -> long spread:gasoline_crack next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=25 hit_rate=0.6 avg_return=1.1356951427459716 excess=0.8280383463909751 sharpe_like=1.353625321130338 max_dd=-14.526260101098158
- OOS (war period): n=8 hit=0.875 avg=2.4590722918510437
- Actionability: 6.96
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
