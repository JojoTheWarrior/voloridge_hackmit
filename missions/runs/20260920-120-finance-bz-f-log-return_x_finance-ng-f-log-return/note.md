# M20260920-8d4551

| Field | Value |
|---|---|
| Mission id | `M20260920-8d4551` |
| Folder | `20260920-120-finance-bz-f-log-return_x_finance-ng-f-log-return` |
| Indicators | `finance.BZ=F.log_return` × `finance.NG=F.log_return` |
| n_obs | 39 |
| r | -0.21179258001903334 |
| Best lag | -4 (days) |
| perm_p | 0.5249500998003992 |
| Bonferroni | 1.0 |
| pre/post Δr | 0.4975194211448103 |
| Fisher p | 0.11643399680038266 |
| Scores | {'validity': 0.12, 'interestingness': 3.26, 'unexpectedness': 5.98, 'supported_prob': 0.02, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.BZ=F.log_return` (configured analysis window); `finance.NG=F.log_return` (configured analysis window) |

## Research note: Brent → US natural gas coupling as a proxy for war-driven delivered-coal cost

**1. Verdict:** Not supported — Brent and Henry Hub log-returns show no positive post-war coupling (post-war r ≈ 0.00, p = 0.99; permutation p = 0.52), and the sign is opposite to expectation.

**2. What the data shows**
- n = 39 paired observations, 2025-03-27 to 2026-09-15 (sparse for a nominally daily pair — likely resampled/aligned, so treat as ~weekly-scale).
- Full-sample Pearson r = −0.21 (p = 0.20); Spearman −0.21 (p = 0.21).
- Best lag −4 (NG leading Brent), r = −0.36; 21 lags tested, Bonferroni p = 1.0 — no lag survives.
- Pre-war (n = 19): r = −0.50 (p = 0.03). Post-war (n = 20): r ≈ 0 (p = 0.99). Change +0.50, Fisher z p = 0.12 — a *loss* of (negative) co-movement, not the emergence of positive coupling.
- No event study was run.

**3. Confounders and caveats**
- Proxy mismatch: the plan tests oil–gas return correlation, which says nothing directly about EIA-923 delivered coal cost; coal cost is monthly, contract-based and dominated by rail/mine-mouth terms.
- n ≈ 20 per regime makes the pre-war r = −0.50 fragile; one or two winter gas spikes (Jan–Feb 2026 cold) could drive it.
- Gas seasonality (heating/storage cycle) and the war itself as a common cause of both series.
- US gas is largely insulated from Hormuz (LNG export capacity-bound), so a null here is expected regardless of coal.
- 21 lags plus two sub-periods → multiple testing; the permutation p already says the headline is noise.

**4. Follow-up mission**
Pull PUDL EIA-923 fuel_receipts_costs (freq=M): compare delivered coal $/MMBtu by rail vs barge vs mine-mouth plants, Mar–Jun 2026 vs the same months 2025, against the FRED diesel (GASDESW) series and rail carload data, with an event study on 2026-03-04 and 2026-06-18.
