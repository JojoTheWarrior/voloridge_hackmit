# R2-0099

| Field | Value |
|---|---|
| Mission id | `R2-0099` |
| Folder | `20260920-199-finance-bz-f-log-return_x_finance-zc-f-log-return` |
| Indicators | `finance.BZ=F.log_return` × `finance.ZC=F.log_return` |
| n_obs | 390 |
| r | 0.15234116324337094 |
| Best lag | 0 (days) |
| perm_p | 0.001996007984031936 |
| Bonferroni | 0.021956087824351295 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.91, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.BZ=F.log_return` (configured analysis window); `finance.ZC=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.15234116324337094, n=390).

The best tested lag was 0 days with r=0.15234116324337088.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZC=F**, hold 1d
- Entry: finance.BZ=F.log_return rolling_zscore_20d > 1 at close -> long ZC=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=50 hit_rate=0.44 avg_return=2.166143084822103e-05 excess=-0.0005087923407864875 sharpe_like=0.013894998838771768 max_dd=-0.05937473792338588
- OOS (war period): n=16 hit=0.375 avg=-0.0005694519347169691
- Actionability: 0.91
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
