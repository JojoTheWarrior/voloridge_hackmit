"""Write a self-contained HTML snapshot of the terminal state."""
from __future__ import annotations

from pathlib import Path

from warsignal.mission.monitor import Monitor

from .app import index_html, run_detail


def write_snapshot(monitor: Monitor, out_path: Path) -> Path:
    """Render the terminal UI with the current state embedded; no polling.

    Run details (stats, scores, note.md) are embedded per folder so the
    detail pane works without the server; viz.png is not embedded.
    """
    monitor.refresh()
    state = dict(monitor.state())
    state["run_details"] = {
        r["folder"]: d
        for r in state.get("runs", [])
        if r.get("folder") and (d := run_detail(monitor, r["folder"])) is not None
    }
    out = Path(out_path)
    out.write_text(index_html(state), encoding="utf-8")
    return out
