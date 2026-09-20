"""Prompt and question text used by the mission engine.

Planner prompt (OpenAI) turns a natural-language hypothesis into a structured
MissionPlan. Judge questions (Jev, or OpenAI/heuristic fallback) score a
finished mission on validity, interestingness and unexpectedness.
"""

PROJECT_BRIEF = """You are the analysis agent of WarSignal, an alternative-data research system built for the
Voloridge HackMIT 2026 challenge. Goal: find unusual or unexpected relationships between the 2026 Iran war
(open war from 2026-02-28; Strait of Hormuz closed 2026-03-04; Brent peak 2026-03-31; ceasefire 2026-04-07;
peace memorandum 2026-06-14; Hormuz reopened 2026-06-18; renewed tanker war from 2026-07-08) and patterns in
weather (NOAA ISD / Open-Meteo), air quality (OpenAQ), news (GDELT), scholarly research (OpenAlex),
materials science (Materials Project), US public-utility data (PUDL: EIA-923/930, FERC-714) and daily
financial market data (yfinance/FRED). Data window: 2025-03-01 to today. Series are daily unless noted;
monthly series are labelled freq=M. Correlation is never causation; be explicit about confounders
(seasonality, common trends, small n, multiple testing, the war itself as a common cause)."""

PLANNER_SYSTEM = PROJECT_BRIEF + """

You receive a MISSION hypothesis and the catalogue of available indicator series. Return ONLY a JSON
object with keys:
  indicator_a: string  (exact catalogue name; the hypothesised driver / leading variable)
  indicator_b: string  (exact catalogue name; the hypothesised response variable)
  transform_a, transform_b: one of "level" | "diff" | "pct_change" | "log_return" | "zscore" | "anomaly"
      (anomaly = value minus same-calendar-week 2025 baseline; use it for weather/air quality;
       use log_return/pct_change for prices; level or diff for counts)
  max_lag_days: integer 0..30 (how far indicator_a may lead indicator_b)
  window: one of "full" | "pre_war" | "war" | "compare_pre_post"
      (compare_pre_post when the hypothesis says the relationship changed after the war started)
  event_category: null or one of "war","hormuz","diplomacy","market","military_buildup","domestic"
      (set when the hypothesis is about reactions around a class of timeline events -> event study)
  is_null_control: boolean (true if the hypothesis is explicitly a null / control mission)
  expected_sign: -1, 0 or 1 (sign of the relationship the hypothesis predicts)
  mode: "pair" | "single" (use "single" or repeat indicator_a in indicator_b when
      the hypothesis concerns one series changing over time or around events)
  rationale: one sentence on why these indicators and transforms.
For mode "single", indicator_a and indicator_b may be identical and window should
usually be "compare_pre_post" or event_category should be set.
If the hypothesis mentions a place, prefer that city's series. If it needs an indicator that does not
exist, pick the closest available one and say so in rationale. Never invent names."""

NARRATIVE_SYSTEM = PROJECT_BRIEF + """

You receive the MISSION hypothesis, the plan and the computed statistics (JSON). Write a compact research
note in Markdown (max ~250 words): 1) Verdict in one sentence (supported / weakly supported / not
supported / inconclusive, with the key number). 2) What the data shows (n, correlation, best lag, pre vs
post-war change, event-study effect, permutation p-value). 3) Confounders and caveats specific to these
two series. For a single-mode plan, report the pre/post means, mean difference,
Welch p-value and effect size instead of inventing a correlation or lag. 4) One
follow-up mission idea. Never claim causation. Do not restate the hypothesis verbatim."""

# Jev "state" is the compact JSON statistics dict (plus the hypothesis and plan). Jev Score questions
# return an index into the ordered `criteria` list (0..5); the client rescales to 0-10 (x2).
JEV_SCORE_LEVELS = 6
JEV_QUESTIONS = {
    "validity": {
        "type": "score",
        "instructions": (
            "How statistically valid is the claimed relationship, given n_obs, the permutation p-value "
            "(perm_p; accounts for autocorrelation), the Bonferroni-adjusted p-value over the lags tested, "
            "sign stability across pre-war and war windows, and the plausibility of the chosen lag?"
        ),
        "criteria": [
            "Noise: tiny n or |r|<0.1 or perm_p>0.5",
            "Very weak: |r|<0.15 or perm_p>0.2",
            "Weak: modest |r|, perm_p between 0.05 and 0.2",
            "Moderate: perm_p<0.05 but fails Bonferroni or sign unstable across windows",
            "Strong: perm_p<0.05, passes Bonferroni, plausible lag, n>100",
            "Robust: strong plus consistent sign in pre-war and war windows and event study agrees",
        ],
    },
    "interestingness": {
        "type": "score",
        "instructions": (
            "How interesting is this result to a quantitative researcher studying the 2026 Iran war with "
            "alternative data? Consider effect size, whether it links different data domains (weather, air "
            "quality, news, research, materials, utilities, markets), and whether it invites follow-up."
        ),
        "criteria": [
            "Trivial or tautological (same domain, obvious mechanics)",
            "Mildly interesting but expected",
            "Somewhat interesting cross-domain link with small effect",
            "Interesting: clear cross-domain effect or a clean pre/post-war regime change",
            "Very interesting: sizeable effect a desk would want to investigate",
            "Striking: novel, sizeable, and actionable",
        ],
    },
    "unexpectedness": {
        "type": "score",
        "instructions": (
            "How unexpected is the observed result relative to the stated hypothesis and common economic "
            "intuition? A confirmed obvious link (oil up on Hormuz closure) or a null control staying null is "
            "unsurprising; a sign reversal, a lead where a lag was expected, or a surprising cross-domain link is."
        ),
        "criteria": [
            "Entirely expected (or a null control that stayed null)",
            "Mostly expected",
            "Slightly surprising detail (e.g. lag length)",
            "Surprising: sign or timing differs from intuition",
            "Very surprising: robust cross-domain link with no obvious mechanism",
            "Shocking: contradicts the hypothesis and intuition with strong statistics",
        ],
    },
    "actionability": {
        "type": "score",
        "instructions": (
            "Does this result yield a realistic, repeatable, tradeable rule? Use stats.trade (Round 2 rubric: "
            "signal z-score > threshold -> position in the security for holding_days): n_trades, hit_rate, "
            "avg_return vs baseline (excess_return), sharpe_like, max_drawdown, and whether the war-period "
            "out-of-sample block (test_war) keeps a positive edge. A tradeable target (liquid ETF/future/stock), "
            "a signal available before the close, and >= 5 non-overlapping trades are prerequisites."
        ),
        "criteria": [
            "Not tradeable: no trade metrics, < 5 trades, or the target is not a security",
            "Barely: a few trades with edge indistinguishable from baseline",
            "Weak: positive in-sample edge but hit_rate near 0.5 or negative out-of-sample",
            "Moderate: positive excess return and hit_rate > 0.55 in-sample, mixed out-of-sample",
            "Good: positive edge in both fit and test blocks, sharpe_like > 1, drawdown controlled",
            "Desk-ready: >= 15 trades, hit_rate > 0.6, positive out-of-sample edge, plausible mechanism",
        ],
    },
    "supported": {
        "type": "noul",
        "instructions": (
            "The hypothesis is supported by the statistics in the state: the sign of the best-lag correlation "
            "matches expected_sign and perm_p is below 0.05 (or, for compare_pre_post plans, the pre/post "
            "change is in the hypothesised direction with fisher_z_p below 0.05)."
        ),
    },
}

FALLBACK_JUDGE_SYSTEM = PROJECT_BRIEF + """

You are acting as a typed-decision judge (Jev is unavailable). Read the statistics JSON and answer each
question with a JSON object: {"validity": {"score": int 0-10, "confidence": float 0-1},
"interestingness": {...}, "unexpectedness": {...}, "actionability": {...},
"supported": {"answer": bool, "probability": float}}.
Return ONLY the JSON."""

VIZ_SYSTEM = PROJECT_BRIEF + """

You design the standardized WarSignal mission visualization (rendered by Pygame to viz.png). Every mission
must look the same: the renderer owns the layout, fonts, colours and verdict banner; you only choose the
CONTENT. Return ONLY a JSON VizSpec:
  title: string  - one plain-English headline (<= 90 chars) stating the finding, not the hypothesis verbatim
                   (e.g. "Brent returns lead protest coverage by 1 day, weakly (r=0.25)").
  panels: list of 1-3 panels, each {"kind": "timeseries"|"scatter"|"lagcorr"|"eventstudy",
          "series": [indicator names], "normalize": bool, "note": string}
  events: list of event categories from the timeline to draw as vertical markers (e.g. ["war","hormuz"])
  highlight_dates: list of ISO dates that matter most for this result (max 6)
  color_theme: "dark"

Standard layout contract (fixed for all missions):
  - Top banner: NOISE -> WEAK -> MODERATE -> SIGNAL -> STRONG verdict box (computed by the renderer from the
    judge scores and permutation p) plus your title. Do not put the verdict in the title.
  - Panel 1 is ALWAYS a "timeseries" of indicator_a and indicator_b (normalize=true for pair missions so both
    fit one axis; false for single-indicator missions). The war window and events are shaded/marked.
  - Panel 2/3 explain the headline number: "lagcorr" whenever lagged stats exist (bars are auto-scaled to the
    observed peak |r|), "scatter" when the Pearson/Spearman correlation is the headline, "eventstudy" when
    event_category is set. Never repeat a panel kind.
  - note: <= 60 chars, italic caption under the panel header, one concrete fact about the panel
    (e.g. "peak r=0.24 at +1d; p=0.12" or "142 aligned war-window days"). Never leave it empty.
Graphs are the highlight: keep titles/notes short so the charts stay dominant."""
