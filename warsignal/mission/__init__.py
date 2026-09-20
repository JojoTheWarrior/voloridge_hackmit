from .model import MissionPlan, MissionResult


def __getattr__(name):
    if name == "run_mission":
        from .runner import run_mission

        return run_mission
    raise AttributeError(name)
