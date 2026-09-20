# R2-0181

| Field | Value |
|---|---|
| Mission id | `R2-0181` |
| Folder | `20260920-268-gdelt-irn-fight-events_x_finance-uae-log-return` |
| Indicators | `gdelt.irn.fight_events` × `finance.UAE.log_return` |
| n_obs | 390 |
| r | -0.17631491917021233 |
| Best lag | -1 (days) |
| perm_p | 0.027944111776447105 |
| Bonferroni | 0.5868263473053892 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.78, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.fight_events` (configured analysis window); `finance.UAE.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.17631491917021233, n=390).

The best tested lag was -1 days with r=-0.1891399591225749.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short UAE**, hold 1d
- Entry: gdelt.irn.fight_events rolling_zscore_20d > 1 at close -> short UAE next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=59 hit_rate=0.4915254237288136 avg_return=0.0007586063939305442 excess=0.0013279129836879693 sharpe_like=0.5413007159363411 max_dd=-0.05610824941565096
- OOS (war period): n=18 hit=0.6666666666666666 avg=0.0032104296868253703
- Actionability: 6.78
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
