from warsignal.mission.model import MissionPlan, MissionResult
from warsignal.mission.results import append_result, load_results


def test_results_roundtrip(tmp_path):
    path = tmp_path / "results.csv"
    result = MissionResult("M1", "now", "test", MissionPlan("a", "b"))
    append_result(result, path)
    append_result(result, path)
    assert len(load_results(path)) == 2
    assert "pearson_r" in result.to_row()
