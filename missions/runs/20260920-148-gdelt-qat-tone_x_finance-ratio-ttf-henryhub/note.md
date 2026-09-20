# R2-0024

| Field | Value |
|---|---|
| Mission id | `R2-0024` |
| Folder | `20260920-148-gdelt-qat-tone_x_finance-ratio-ttf-henryhub` |
| Indicators | `gdelt.qat.tone` × `finance.ratio.ttf_henryhub` |
| n_obs | 390 |
| r | -0.09990376330013183 |
| Best lag | -1 (days) |
| perm_p | 0.4291417165668663 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.42, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.qat.tone` (configured analysis window); `finance.ratio.ttf_henryhub` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.09990376330013183, n=390).

The best tested lag was -1 days with r=-0.1258444240703938.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ratio:ttf_henryhub**, hold 1d
- Entry: gdelt.qat.tone rolling_zscore_20d > 1 at close -> long ratio:ttf_henryhub next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=51 hit_rate=0.6274509803921569 avg_return=0.007558638863363161 excess=0.002472015946215096 sharpe_like=0.9661210083356867 max_dd=-0.2747310243568636
- OOS (war period): n=18 hit=0.6666666666666666 avg=0.013063977112809329
- Actionability: 7.42
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
