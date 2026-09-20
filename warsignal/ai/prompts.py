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
  rationale: one sentence on why these indicators and transforms.
If the hypothesis mentions a place, prefer that city's series. If it needs an indicator that does not
exist, pick the closest available one and say so in rationale. Never invent names."""

NARRATIVE_SYSTEM = PROJECT_BRIEF + """

You receive the MISSION hypothesis, the plan and the computed statistics (JSON). Write a compact research
note in Markdown (max ~250 words): 1) Verdict in one sentence (supported / weakly supported / not
supported / inconclusive, with the key number). 2) What the data shows (n, correlation, best lag, pre vs
post-war change, event-study effect, permutation p-value). 3) Confounders and caveats specific to these
two series. 4) One follow-up mission idea. Never claim causation. Do not restate the hypothesis verbatim."""

# Jev "state" is the compact JSON statistics dict; these are the questions asked against it.
JEV_QUESTIONS = {
    "validity": {
        "type": "score",
        "question": (
            "On a 0-10 scale, how statistically valid is the claimed relationship, given the sample size, "
            "the permutation p-value (which accounts for autocorrelation), the stability of the sign across "
            "pre-war and war windows, and the plausibility of the chosen lag? 0 = noise, 10 = robust."
        ),
        "min": 0,
        "max": 10,
    },
    "interestingness": {
        "type": "score",
        "question": (
            "On a 0-10 scale, how interesting is this result to a quantitative researcher studying the 2026 "
            "Iran war with alternative data? Consider effect size, whether it links different data domains "
            "(weather, air quality, news, research, materials, utilities, markets), and whether it could be "
            "acted on or investigated further. 0 = trivial/tautological, 10 = striking."
        ),
        "min": 0,
        "max": 10,
    },
    "unexpectedness": {
        "type": "score",
        "question": (
            "On a 0-10 scale, how unexpected is the observed result relative to the stated hypothesis and "
            "common economic intuition? A confirmed obvious link (oil up on Hormuz closure) scores low; a "
            "sign reversal, a lead where a lag was expected, or a cross-domain link scores high. Null "
            "controls that stay null score low."
        ),
        "min": 0,
        "max": 10,
    },
    "supported": {
        "type": "noul",
        "question": "Is the hypothesis supported by the statistics in the state (sign matches expectation and permutation p-value below 0.05)?",
    },
}

FALLBACK_JUDGE_SYSTEM = PROJECT_BRIEF + """

You are acting as a typed-decision judge (Jev is unavailable). Read the statistics JSON and answer each
question with a JSON object: {"validity": {"score": int 0-10, "confidence": float 0-1},
"interestingness": {...}, "unexpectedness": {...}, "supported": {"answer": bool, "probability": float}}.
Return ONLY the JSON."""

VIZ_SYSTEM = PROJECT_BRIEF + """

You design an interactive Pygame visualization for a finished mission. Return ONLY a JSON VizSpec:
  title: string
  panels: list of 1-3 panels, each {"kind": "timeseries"|"scatter"|"lagcorr"|"eventstudy",
          "series": [indicator names], "normalize": bool, "note": string}
  events: list of event categories from the timeline to draw as vertical markers (e.g. ["war","hormuz"])
  highlight_dates: list of ISO dates that matter most for this result (max 6)
  color_theme: "dark"|"light"
Choose panels that make the specific finding visible (e.g. a lagcorr panel when best lag != 0;
an eventstudy panel when event_category is set; scatter when correlation is the headline)."""
