from warsignal.mission.planner import heuristic_plan


def test_heuristic_plan():
    plan = heuristic_plan("Tehran temperature vs Brent")
    assert plan.indicator_a.startswith("weather.tehran.")
    assert plan.indicator_b.startswith("finance.BZ=F.")


def test_heuristic_plan_uses_distinct_sources_for_news_and_oil():
    plan = heuristic_plan("GDELT news volume mentioning Iran vs Brent crude returns")
    assert plan.indicator_a.startswith("gdelt.")
    assert plan.indicator_b.startswith("finance.BZ=F.")
