"""Write a self-contained HTML snapshot of the terminal state."""
from __future__ import annotations

from pathlib import Path

from warsignal.mission.monitor import Monitor

from .app import snapshot_html


def write_snapshot(monitor: Monitor, out_path: Path) -> Path:
    """Render the terminal UI with the current state embedded; no polling.

    Run details (stats, scores, note.md) are embedded per folder so the
    detail pane works without the server; viz.png is not embedded.
    """
    monitor.refresh()
    out = Path(out_path)
    out.write_text(snapshot_html(monitor), encoding="utf-8")
    return out
