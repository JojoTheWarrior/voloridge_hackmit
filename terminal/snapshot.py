"""Write a self-contained HTML snapshot of the terminal state."""
from __future__ import annotations

from pathlib import Path

from warsignal.mission.monitor import Monitor

from .app import index_html


def write_snapshot(monitor: Monitor, out_path: Path) -> Path:
    """Render the terminal UI with the current state embedded; no polling."""
    monitor.refresh()
    out = Path(out_path)
    out.write_text(index_html(monitor.state()), encoding="utf-8")
    return out
