import pytest

from warsignal.indicators import REGISTRY
from warsignal.mission.model import MissionPlan
from warsignal.mission.planner import PlanValidationError, _validate_plan, heuristic_plan


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
