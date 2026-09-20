# S-0007

| Field | Value |
|---|---|
| Mission id | `S-0007` |
| Folder | `20260920-211-utility-generation-hydro-mwh_x_finance-fred-dhhngsp` |
| Indicators | `utility.generation.hydro_mwh` × `finance.fred.DHHNGSP` |
| n_obs | 15 |
| r | -0.09097995469679329 |
| Best lag | 0 (months) |
| perm_p | 0.6626746506986028 |
| Bonferroni | 0.6626746506986028 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `utility.generation.hydro_mwh` (configured analysis window); `finance.fred.DHHNGSP` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.09097995469679329, n=15).

The best tested lag was 0 months with r=-0.09097995469679329.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short fred:DHHNGSP**, hold 1d
- Entry: utility.generation.hydro_mwh rolling_zscore_20d > 1 at close -> short fred:DHHNGSP next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=0 hit_rate=None avg_return=None excess=None sharpe_like=None max_dd=None
- OOS (war period): n=0 hit=None avg=None
- Actionability: 0.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
