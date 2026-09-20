# M20260920-a1ce90

| Field | Value |
|---|---|
| Mission id | `M20260920-a1ce90` |
| Folder | `20260920-134-utility-us-demand-anomaly_x_gdelt-gkg-hormuz-share` |
| Indicators | `utility.us.demand_anomaly` × `gdelt.gkg.hormuz_share` |
| n_obs | 554 |
| r | 0.016645615387576577 |
| Best lag | 0 (days) |
| perm_p | 0.4311377245508982 |
| Bonferroni | 1.0 |
| pre/post Δr | nan |
| Fisher p | nan |
| Scores | {'validity': 1.7, 'interestingness': 2.7, 'unexpectedness': 0.54, 'supported_prob': 0.03, 'judge_model': 'jev-1.13.0'} |
| Data sources | `utility.us.demand_anomaly` (configured analysis window); `gdelt.gkg.hormuz_share` (configured analysis window) |

## Research note: US demand anomaly vs. Hormuz news share

**1. Verdict.** Not supported: over 554 daily observations the contemporaneous Pearson r between the US electricity-demand anomaly (level) and the daily change in GDELT Hormuz share is 0.017 (p = 0.70), indistinguishable from zero.

**2. What the data shows.**
- n = 554 (2025-03-02 to 2026-09-06). Pearson r = 0.017, Spearman ρ = −0.022; the two rank/linear measures even disagree in sign.
- Lag scan (±3 days, 7 lags): best lag 0 with r = 0.017; permutation p = 0.43; Bonferroni-adjusted p = 1.0.
- Pre/post war: pre-war correlation is undefined (NaN) because Hormuz share was essentially constant at zero before 2026-02-28, so no variance in series B; post-war (n = 191) r = 0.018 (p = 0.81). Fisher-z test not computable.
- Event study (11 Hormuz events): demand anomaly falls by ~266 MWh-equivalent on average (t = −0.54, p = 0.60); Hormuz-share change −0.043 (p = 0.34), but 10 of 11 events show exactly 0.0 pre/post change — only 2026-04-12 has any signal, so the event-study effect is driven by one date.

**3. Confounders and caveats.**
- Series B is degenerate: near-zero pre-war, sparse and spiky post-war; differencing a mostly-zero share produces a few large spikes and many zeros, which suppresses any correlation.
- Demand anomaly is dominated by weather seasonality and weekday effects; the same-weekday-2025 baseline removes some but not all of this, and 2026 heat/cold waves are unrelated to Gulf news.
- Hormuz share measures media attention, not gas-price sensitivity; the stated hypothesis (price sensitivity) is untestable with a daily series in the catalogue.
- The war is a common cause for both post-war attention and any energy-market stress; n_events = 11 is small, and the multiple-lag search inflates false-positive risk (already reflected in Bonferroni p = 1.0).

**4. Follow-up mission.** Replace the attention proxy with a price-based one: test whether daily Henry Hub / TTF proxies (e.g. yfinance UNG or NG=F returns) show larger absolute returns on Hormuz-event days when the demand anomaly is in its top decile (interaction/regime test), restricted to the post-2026-02-28 window.
