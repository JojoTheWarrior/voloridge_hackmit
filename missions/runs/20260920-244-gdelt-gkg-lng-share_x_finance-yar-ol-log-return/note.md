# R2-0146

| Field | Value |
|---|---|
| Mission id | `R2-0146` |
| Folder | `20260920-244-gdelt-gkg-lng-share_x_finance-yar-ol-log-return` |
| Indicators | `gdelt.gkg.lng_share` × `finance.YAR.OL.log_return` |
| n_obs | 386 |
| r | -0.020090324323078293 |
| Best lag | -6 (days) |
| perm_p | 0.23552894211576847 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.6, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.lng_share` (configured analysis window); `finance.YAR.OL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.020090324323078293, n=386).

The best tested lag was -6 days with r=0.10047613140591387.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long YAR**, hold 1d
- Entry: gdelt.gkg.lng_share rolling_zscore_20d > 1 at close -> long YAR next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=51 hit_rate=0.5098039215686274 avg_return=-0.0018433195793695883 excess=-0.0028208224399939633 sharpe_like=-0.6872021892738169 max_dd=-0.13119476109446648
- OOS (war period): n=15 hit=0.4666666666666667 avg=-0.005970074435587672
- Actionability: 1.6
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
