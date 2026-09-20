from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class MissionPlan:
    indicator_a: str
    indicator_b: str
    transform_a: str = "level"
    transform_b: str = "level"
    max_lag_days: int = 0
    window: str = "full"
    event_category: str | None = None
    is_null_control: bool = False
    expected_sign: int = 0
    rationale: str = ""
    mode: str = "pair"


@dataclass
class MissionResult:
    mission_id: str
    created_at: str
    hypothesis: str
    plan: MissionPlan
    stats: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    narrative_md: str = ""
    status: str = "ok"
    error: str | None = None
    artifacts: dict = field(default_factory=dict)
    judge: str = ""
    planner_model: str = ""
    data_sources: list = field(default_factory=list)
    date_start: str | None = None
    date_end: str | None = None
    n_obs: int = 0
    brain_sessions: list = field(default_factory=list)
    trade_idea: dict | None = None

    def to_row(self):
        corr = self.stats.get("correlation") or {}
        lag = self.stats.get("lagged") or {}
        pp = self.stats.get("pre_post") or {}
        event = self.stats.get("event_study") or {}
        return {
            "mission_id": self.mission_id, "created_at": self.created_at, "status": self.status,
            "hypothesis": self.hypothesis, "indicator_a": self.plan.indicator_a, "indicator_b": self.plan.indicator_b,
            "mode": self.plan.mode,
            "transform_a": self.plan.transform_a, "transform_b": self.plan.transform_b, "window": self.plan.window,
            "event_category": self.plan.event_category, "is_null_control": self.plan.is_null_control,
            "expected_sign": self.plan.expected_sign, "data_sources": "|".join(self.data_sources),
            "date_start": self.date_start, "date_end": self.date_end, "n_obs": self.n_obs,
            "pearson_r": corr.get("pearson_r"), "pearson_p": corr.get("pearson_p"),
            "spearman_r": corr.get("spearman_r"), "best_lag": lag.get("best_lag"), "best_lag_r": lag.get("best_r"),
            "perm_p": self.stats.get("perm_p"), "bonferroni_p": self.stats.get("bonferroni_p"),
            "pre_r": (pp.get("pre") or {}).get("pearson_r"), "post_r": (pp.get("post") or {}).get("pearson_r"),
            "r_change": pp.get("r_change"), "fisher_z_p": pp.get("fisher_z_p"), "event_n": event.get("n_events"),
            "event_mean_change": event.get("mean_change"), "event_p": event.get("p"),
            "pre_mean": (pp.get("pre") or {}).get("mean"), "post_mean": (pp.get("post") or {}).get("mean"),
            "mean_diff": pp.get("mean_diff"), "welch_p": pp.get("welch_p"), "cohens_d": pp.get("cohens_d"),
            "sign_matches": self.stats.get("sign_matches_expectation"),
            "validity": self.scores.get("validity"), "interestingness": self.scores.get("interestingness"),
            "unexpectedness": self.scores.get("unexpectedness"), "supported_prob": self.scores.get("supported_prob"),
            "actionability": self.scores.get("actionability"),
            "trade_instrument": (self.trade_idea or {}).get("instrument"),
            "trade_direction": (self.trade_idea or {}).get("direction"),
            "trade_holding_days": (self.trade_idea or {}).get("holding_days"),
            "trade_n": (self.trade_idea or {}).get("n_trades"), "trade_hit_rate": (self.trade_idea or {}).get("hit_rate"),
            "trade_avg_return": (self.trade_idea or {}).get("avg_return"),
            "trade_sharpe_like": (self.trade_idea or {}).get("sharpe_like"),
            "judge": self.judge, "planner_model": self.planner_model,
            "brain_sessions": ";".join(
                item.get("session_url", "") for item in self.brain_sessions if item.get("session_url")
            ),
            "summary": self.narrative_md.splitlines()[0] if self.narrative_md else "",
            "report_path": self.artifacts.get("report_path"), "viz_path": self.artifacts.get("viz_path"),
            "error": self.error,
        }
