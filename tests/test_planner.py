from warsignal.mission.planner import heuristic_plan


def test_heuristic_plan():
    plan = heuristic_plan("Tehran temperature vs Brent")
    assert plan.indicator_a.startswith("weather.tehran.")
    assert plan.indicator_b.startswith("finance.BZ=F.")
