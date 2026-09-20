# R2-0119

| Field | Value |
|---|---|
| Mission id | `R2-0119` |
| Folder | `20260920-227-finance-ttf-f-abs-return_x_gdelt-gkg-lng-share` |
| Indicators | `finance.TTF=F.abs_return` × `gdelt.gkg.lng_share` |
| n_obs | 391 |
| r | 0.48971418608839434 |
| Best lag | 0 (days) |
| perm_p | 0.0499001996007984 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.5, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.TTF=F.abs_return` (configured analysis window); `gdelt.gkg.lng_share` (configured analysis window) |

**Verdict:** supported (Pearson r=0.48971418608839434, n=391).

The best tested lag was 0 days with r=0.48971418608839407.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long gdelt.gkg.lng_share**, hold 1d
- Entry: finance.TTF=F.abs_return rolling_zscore_20d > 1 at close -> long gdelt.gkg.lng_share next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=49 hit_rate=0.8775510204081632 avg_return=1.5490580997329926 excess=-0.0542320375961578 sharpe_like=5.238328887368267 max_dd=0.0
- OOS (war period): n=15 hit=1.0 avg=3.4038367127871423
- Actionability: 8.5
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
