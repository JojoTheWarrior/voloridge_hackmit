# R2-0042

| Field | Value |
|---|---|
| Mission id | `R2-0042` |
| Folder | `20260920-161-gdelt-gkg-oman-share_x_finance-zw-f-log-return` |
| Indicators | `gdelt.gkg.oman_share` × `finance.ZW=F.log_return` |
| n_obs | 390 |
| r | 0.019815551822387024 |
| Best lag | 5 (days) |
| perm_p | 0.17165668662674652 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.oman_share` (configured analysis window); `finance.ZW=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.019815551822387024, n=390).

The best tested lag was 5 days with r=0.12144344152027897.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZW=F**, hold 5d
- Entry: gdelt.gkg.oman_share rolling_zscore_20d > 1 at close -> long ZW=F next session
- Exit: close after 5 trading days (no overlapping entries)
- n_trades=28 hit_rate=0.42857142857142855 avg_return=0.00597704096749679 excess=0.0016212794984892644 sharpe_like=0.8575669976808528 max_dd=-0.09362135710717234
- OOS (war period): n=8 hit=0.5 avg=0.013486278463451032
- Actionability: 6.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
