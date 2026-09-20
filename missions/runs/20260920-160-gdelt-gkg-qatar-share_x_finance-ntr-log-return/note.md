# R2-0040

| Field | Value |
|---|---|
| Mission id | `R2-0040` |
| Folder | `20260920-160-gdelt-gkg-qatar-share_x_finance-ntr-log-return` |
| Indicators | `gdelt.gkg.qatar_share` × `finance.NTR.log_return` |
| n_obs | 390 |
| r | 0.0037398115093013086 |
| Best lag | -5 (days) |
| perm_p | 0.17564870259481039 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.05, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.qatar_share` (configured analysis window); `finance.NTR.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0037398115093013086, n=390).

The best tested lag was -5 days with r=0.1157879482653661.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long NTR**, hold 1d
- Entry: gdelt.gkg.qatar_share rolling_zscore_20d > 1 at close -> long NTR next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=37 hit_rate=0.5405405405405406 avg_return=0.0014172800053556121 excess=0.00012756943213272317 sharpe_like=0.44128546471312596 max_dd=-0.10954116151359305
- OOS (war period): n=7 hit=0.2857142857142857 avg=-0.005796686385674924
- Actionability: 4.05
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
