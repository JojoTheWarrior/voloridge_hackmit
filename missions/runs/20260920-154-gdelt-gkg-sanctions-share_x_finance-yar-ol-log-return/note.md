# R2-0033

| Field | Value |
|---|---|
| Mission id | `R2-0033` |
| Folder | `20260920-154-gdelt-gkg-sanctions-share_x_finance-yar-ol-log-return` |
| Indicators | `gdelt.gkg.sanctions_share` × `finance.YAR.OL.log_return` |
| n_obs | 386 |
| r | -0.027347986767494746 |
| Best lag | -8 (days) |
| perm_p | 0.6027944111776448 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.26, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.sanctions_share` (configured analysis window); `finance.YAR.OL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.027347986767494746, n=386).

The best tested lag was -8 days with r=-0.08441515680735677.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short YAR**, hold 1d
- Entry: gdelt.gkg.sanctions_share rolling_zscore_20d > 1 at close -> short YAR next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=44 hit_rate=0.4772727272727273 avg_return=-0.00046221544832946007 excess=0.0005152874122949149 sharpe_like=-0.16533230422400114 max_dd=-0.13247603641362604
- OOS (war period): n=13 hit=0.6153846153846154 avg=0.007416938780759629
- Actionability: 6.26
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
