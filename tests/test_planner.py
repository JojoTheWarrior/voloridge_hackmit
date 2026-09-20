import pytest

from warsignal.indicators import REGISTRY
from warsignal.mission.model import MissionPlan
from warsignal.mission.planner import (
    PlanValidationError,
    _semantic_adjust,
    _validate_plan,
    heuristic_plan,
)


def test_heuristic_plan():
    plan = heuristic_plan("Tehran temperature vs Brent")
    assert plan.indicator_a.startswith("weather.tehran.")
    assert plan.indicator_b.startswith("finance.BZ=F.")


def test_heuristic_plan_uses_distinct_sources_for_news_and_oil():
    plan = heuristic_plan("GDELT news volume mentioning Iran vs Brent crude returns")
    assert plan.indicator_a.startswith("gdelt.")
    assert plan.indicator_b.startswith("finance.BZ=F.")


def test_city_validation_accepts_any_named_gulf_city():
    plan = MissionPlan("weather.dubai.temp_mean", "gdelt.usa.events")
    assert _validate_plan("Dubai and Doha conditions", plan) == plan


def test_city_validation_rejects_unavailable_requested_city():
    if "airquality.tokyo.pm25" not in REGISTRY:
        pytest.skip("Tokyo OpenAQ PM2.5 is unavailable")
    with pytest.raises(PlanValidationError, match="requested city tehran has no data for airquality"):
        _validate_plan(
            "Tehran PM2.5 versus conflict events",
            MissionPlan("weather.tehran.temp_mean", "airquality.tokyo.pm25"),
        )


def test_semantic_adjust_does_not_clobber_hormuz_brent_plan():
    plan = MissionPlan("gdelt.gkg.hormuz_share", "finance.BZ=F.log_return")
    adjusted = _semantic_adjust("Hormuz news versus Brent returns", plan)
    assert adjusted.indicator_a == "gdelt.gkg.hormuz_share"
    assert adjusted.indicator_b == "finance.BZ=F.log_return"


def test_identical_indicators_become_single_mode():
    plan = MissionPlan("gdelt.irn.tone", "gdelt.irn.tone")
    assert _validate_plan("Iran news tone changed", plan).mode == "single"


def test_tone_only_heuristic_does_not_choose_weather():
    plan = heuristic_plan("Average GDELT tone of Iran-related news is more negative before strikes")
    assert plan.mode == "single"
    assert plan.indicator_a == "gdelt.irn.tone"
    assert plan.indicator_b == "gdelt.irn.tone"
