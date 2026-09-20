# R2-0092

| Field | Value |
|---|---|
| Mission id | `R2-0092` |
| Folder | `20260920-195-gdelt-irn-mentions_x_finance-spy-log-return` |
| Indicators | `gdelt.irn.mentions` × `finance.SPY.log_return` |
| n_obs | 390 |
| r | 0.010700126890134403 |
| Best lag | -10 (days) |
| perm_p | 0.9201596806387226 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.18, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.mentions` (configured analysis window); `finance.SPY.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.010700126890134403, n=390).

The best tested lag was -10 days with r=-0.04912512646229328.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long SPY**, hold 1d
- Entry: gdelt.irn.mentions rolling_zscore_20d > 1 at close -> long SPY next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=47 hit_rate=0.46808510638297873 avg_return=-0.0003808263649266476 excess=-0.0012381763646710604 sharpe_like=-0.3422066299750393 max_dd=-0.05585009888795667
- OOS (war period): n=13 hit=0.6153846153846154 avg=0.0009993069335669192
- Actionability: 4.18
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
