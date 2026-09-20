# R2-0141

| Field | Value |
|---|---|
| Mission id | `R2-0141` |
| Folder | `20260920-241-gdelt-gkg-oman-share_x_finance-spy-log-return` |
| Indicators | `gdelt.gkg.oman_share` × `finance.SPY.log_return` |
| n_obs | 390 |
| r | 0.05519281445441093 |
| Best lag | 8 (days) |
| perm_p | 0.8882235528942116 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 9.84, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.oman_share` (configured analysis window); `finance.SPY.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.05519281445441093, n=390).

The best tested lag was 8 days with r=-0.06085392419536397.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long SPY**, hold 8d
- Entry: gdelt.gkg.oman_share rolling_zscore_20d > 1 at close -> long SPY next session
- Exit: close after 8 trading days (no overlapping entries)
- n_trades=22 hit_rate=0.7727272727272727 avg_return=0.01226704059171308 excess=0.005462120908566462 sharpe_like=2.81462920119196 max_dd=-0.03412873268391825
- OOS (war period): n=6 hit=0.8333333333333334 avg=0.018905386352053744
- Actionability: 9.84
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
