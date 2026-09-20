# R2-0140

| Field | Value |
|---|---|
| Mission id | `R2-0140` |
| Folder | `20260920-239-gdelt-gkg-qatar-share_x_finance-mos-log-return` |
| Indicators | `gdelt.gkg.qatar_share` × `finance.MOS.log_return` |
| n_obs | 390 |
| r | -0.06369818594017815 |
| Best lag | 9 (days) |
| perm_p | 0.09780439121756487 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.qatar_share` (configured analysis window); `finance.MOS.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.06369818594017815, n=390).

The best tested lag was 9 days with r=-0.1447473062659533.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short MOS**, hold 9d
- Entry: gdelt.gkg.qatar_share rolling_zscore_20d > 1 at close -> short MOS next session
- Exit: close after 9 trading days (no overlapping entries)
- n_trades=21 hit_rate=0.38095238095238093 avg_return=-0.011999384867108557 excess=-0.009983798096895466 sharpe_like=-0.801739590685749 max_dd=-0.23161035667208507
- OOS (war period): n=5 hit=0.4 avg=-0.028972449175304373
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
