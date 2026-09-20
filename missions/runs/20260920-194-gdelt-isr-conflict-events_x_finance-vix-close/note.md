# R2-0090

| Field | Value |
|---|---|
| Mission id | `R2-0090` |
| Folder | `20260920-194-gdelt-isr-conflict-events_x_finance-vix-close` |
| Indicators | `gdelt.isr.conflict_events` × `finance.^VIX.close` |
| n_obs | 391 |
| r | 0.08613826695062553 |
| Best lag | -1 (days) |
| perm_p | 0.07784431137724551 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.78, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.isr.conflict_events` (configured analysis window); `finance.^VIX.close` (configured analysis window) |

**Verdict:** supported (Pearson r=0.08613826695062553, n=391).

The best tested lag was -1 days with r=0.1292858881505873.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ^VIX**, hold 1d
- Entry: gdelt.isr.conflict_events rolling_zscore_20d > 1 at close -> long ^VIX next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=59 hit_rate=0.423728813559322 avg_return=0.0006013600772805707 excess=-0.0011575152012554932 sharpe_like=0.06797637195743104 max_dd=-0.46122669782483205
- OOS (war period): n=18 hit=0.5 avg=0.014817471046423392
- Actionability: 2.78
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
