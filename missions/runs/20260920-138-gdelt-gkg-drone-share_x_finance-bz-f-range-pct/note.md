# R2-0009

| Field | Value |
|---|---|
| Mission id | `R2-0009` |
| Folder | `20260920-138-gdelt-gkg-drone-share_x_finance-bz-f-range-pct` |
| Indicators | `gdelt.gkg.drone_share` × `finance.BZ=F.range_pct` |
| n_obs | 391 |
| r | 0.41736395272141685 |
| Best lag | 3 (days) |
| perm_p | 0.023952095808383235 |
| Bonferroni | 0.16766467065868265 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.06, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.drone_share` (configured analysis window); `finance.BZ=F.range_pct` (configured analysis window) |

**Verdict:** supported (Pearson r=0.41736395272141685, n=391).

The best tested lag was 3 days with r=0.46147642801290567.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long BZ=F**, hold 3d
- Entry: gdelt.gkg.drone_share rolling_zscore_20d > 1 at close -> long BZ=F next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=25 hit_rate=1.0 avg_return=0.10341607559053419 excess=-0.019601354549478103 sharpe_like=9.309320115798688 max_dd=0.0
- OOS (war period): n=8 hit=1.0 avg=0.14676009209971697
- Actionability: 5.06
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
