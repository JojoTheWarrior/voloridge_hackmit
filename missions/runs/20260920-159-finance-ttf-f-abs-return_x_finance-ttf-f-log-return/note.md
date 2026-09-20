# R2-0037

| Field | Value |
|---|---|
| Mission id | `R2-0037` |
| Folder | `20260920-159-finance-ttf-f-abs-return_x_finance-ttf-f-log-return` |
| Indicators | `finance.TTF=F.abs_return` × `finance.TTF=F.log_return` |
| n_obs | 391 |
| r | 0.2265516306766731 |
| Best lag | 0 (days) |
| perm_p | 0.029940119760479042 |
| Bonferroni | 0.6287425149700598 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.19, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.TTF=F.abs_return` (configured analysis window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.2265516306766731, n=391).

The best tested lag was 0 days with r=0.22655163067667308.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short TTF=F**, hold 1d
- Entry: finance.TTF=F.abs_return rolling_zscore_20d > 1 at close -> short TTF=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=49 hit_rate=0.46938775510204084 avg_return=-0.005894501250310526 excess=-0.0033998340859925655 sharpe_like=-0.9100084187451783 max_dd=-0.416212964856678
- OOS (war period): n=15 hit=0.4 avg=-0.02105417455774871
- Actionability: 0.19
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
