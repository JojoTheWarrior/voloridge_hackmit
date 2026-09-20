from __future__ import annotations

import shutil
from pathlib import Path

from .queue import mark_done, mark_failed, pop_next, requeue_failed
from .results import append_result
from .runner import run_mission


ROOT = Path(__file__).resolve().parents[2]


def reset_queue():
    missions = ROOT / "missions"
    shutil.copyfile(missions / "queue_original.txt", missions / "queue.txt")
    (missions / "in_progress.txt").write_text("", encoding="utf-8")


def requeue_failed_missions():
    return requeue_failed()


def run_queue(n=None, use_ai=True, stop_on_error=False, viz=False, max_retries=1, publish=False):
    results = []
    while n is None or len(results) < n:
        line = pop_next()
        if line is None:
            break
        result = run_mission(line, use_ai=use_ai, viz=viz, publish=publish)
        if (
            result.status == "failed"
            and use_ai
            and max_retries > 0
            and "insufficient overlap" in (result.error or "")
        ):
            retry_result = run_mission(line, use_ai=False, viz=viz, publish=publish)
            if retry_result.status == "failed":
                retry_result.error = f"{retry_result.error}; retried with heuristic plan"
            result = retry_result
        append_result(result)
        if result.status == "ok":
            mark_done(line)
        else:
            mark_failed(line, result.error or "mission failed")
            if stop_on_error:
                break
        results.append(result)
        print(f"{result.mission_id} | validity {result.scores.get('validity', 0):.1f} | interest {result.scores.get('interestingness', 0):.1f} | unexpected {result.scores.get('unexpectedness', 0):.1f} | {result.status}", flush=True)
    rows = sorted(results, key=lambda r: (r.scores.get("interestingness", 0) + r.scores.get("unexpectedness", 0)), reverse=True)
    summary = ROOT / "missions" / "summary.md"
    with summary.open("w", encoding="utf-8") as handle:
        handle.write("# Mission Summary\n\n")
        for result in rows[:10]:
            handle.write(f"- **{result.mission_id}** ({result.scores.get('interestingness', 0):.1f} + {result.scores.get('unexpectedness', 0):.1f}): {result.narrative_md.splitlines()[0] if result.narrative_md else result.error}\n")
    return results
