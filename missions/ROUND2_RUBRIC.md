# Round 2 trade rubric (Iran war / Strait of Hormuz)

Round 1 asked "is there a correlation?". Round 2 asks "is there a **rule** a trader
could re-run tomorrow?". Every Round 2 mission therefore ends with a `trade_idea`
(see `missions/status/SCHEMA.md`) computed by `warsignal/analysis/trade.py` and an
`actionability` score (0–10) that sits next to Jev's validity / interestingness /
unexpectedness in `results.csv`, `manifest.json`, and `missions/runs/INDEX.md`.

## Hypothesis format

One line, prefixed `R2 |`, ending with an explicit indicator tag that the planner
honours verbatim (`warsignal.mission.planner.explicit_plan`):

```
R2 | [oil-shipping] GDELT Hormuz GKG share 20d z-score > 1.5 leads FRO log returns by 2 days (+); trade long FRO 3d [gdelt.gkg.hormuz_share -> finance.FRO.log_return]
```

* `[signal -> target]`: two registered indicator names (`python main.py indicators`).
  The **target** must be a tradeable finance series (`finance.<TICKER>.log_return`,
  `finance.<TICKER>.close`, `finance.spread.*`, `finance.ratio.*`).
* `(+)` / `(-)`: expected sign; `(-)` means the rule **shorts** the target.
* Lag / window: `by N days`, `Nd` etc. The largest number of days found becomes
  `max_lag_days` (clipped to 3..10).
* Follow-ups append ` (parent: R2-00NN)`.

## The rule

Given the aligned mission series (`signal` = indicator_a after the planned
transform, `target` = indicator_b):

1. `z_t = (signal_t - mean_{t-20..t-1}) / std_{t-20..t-1}` — rolling **20-day**
   z-score, computed causally (`rolling_zscore`).
2. **Entry:** at the close of day `t` when `z_t > 1.0` (`threshold`).
3. **Position:** long the target if expected sign is `+`, short if `-`.
4. **Holding period:** `holding_days` = the best positive lag from the mission's
   lagged-correlation scan (signal leads target), clipped to 1..10 days.
5. **No overlap:** a new entry is ignored while a position is open, so trades are
   independent observations.
6. **P&L unit:** `finance.*.log_return` → exponentiated simple returns;
   `.close` / `ratio.*` → percent change; `spread.*` → point change (spreads
   can cross zero). Forward returns never look past the last observation and
   missing returns are **not** forward-filled.

## Metrics (`trade.json`)

For **all trades**, the **pre-war fit** (`< 2026-02-28`) and the **war test**
(`>= 2026-02-28`, out-of-sample):

| field | meaning |
|---|---|
| `n_trades` | non-overlapping entries |
| `hit_rate` | share of trades with positive P&L |
| `avg_return` | mean per-trade return |
| `baseline_avg_return` | mean return of *every* `holding_days` window in the same period, same direction (the unconditional baseline) |
| `excess_return` | `avg_return - baseline_avg_return` |
| `sharpe_like` | `mean / std * sqrt(n_trades)` over trades (t-stat-like, not annualised) |
| `max_drawdown` | worst peak-to-trough of the trade-by-trade equity curve |
| `total_return` | compounded return of the trade sequence |

## Actionability (0–10)

Jev is asked the `actionability` question in `warsignal/ai/prompts.py`. Without a
Jev/OpenAI key the deterministic fallback `heuristic_actionability` is used:

```
< 5 trades                       -> 0.4 * n_trades            (max 2)
start at 2
+ min(2, 2*log10(n/5 + 1))       sample size
+ clip((hit_rate - 0.5) * 10, -2, 2)
+ 1 if excess_return > 0 else -1
+ min(2, sharpe_like / 1.5)
+ 1.5 if war-test excess > 0 and war-test n >= 3, else -1 if war-test n >= 3 and excess < 0
- 1 if max_drawdown < -15 %
clip to 0..10
```

Interpretation: ≥7 = repeatable, ≥5 = worth a follow-up, <3 = story not a rule.

## Caveats the report must carry

Daily closes, no costs or slippage; the war is a common cause of both the signal
and the target; the war-period test is short (few independent regimes); the
threshold and window are fixed (1.0 / 20d) to avoid over-fitting per mission;
Bonferroni-adjusted permutation p from the correlation stage is still reported and
should be read alongside the trade metrics.
