"""Background ``git pull --rebase --autostash`` loop for live mission status.

Kingdom treats GitHub ``main`` as the source of truth for
``missions/status/*.json``; a daemon thread re-pulls every ``interval``
seconds and ``tick()`` tells the caller when a pull finished so it can
refresh the data adapter. Everything is best-effort: errors are recorded in
``last_error`` and never raised.
"""
from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

PULL_CMD = ["git", "pull", "--rebase", "--autostash", "--quiet"]


class GitSync:
    def __init__(self, root: Path, interval: float = 60.0, enabled: bool = True, runner=subprocess.run):
        self.root = Path(root)
        self.interval = float(interval)
        self.enabled = bool(enabled) and (self.root / ".git").exists()
        self.runner = runner
        self.status: str = "ok" if self.enabled else "off"  # off | syncing | ok | error
        self.last_ok: Optional[float] = None
        self.last_error: str = ""
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._finished = False
        self._stopped = False
        self._last_started: Optional[float] = None

    def start(self) -> None:
        """Kick off the first pull immediately on a background thread."""
        if not self.enabled:
            self.status = "off"
            return
        self._launch(time.time(), force=True)

    def _launch(self, now: float, force: bool = False) -> bool:
        with self._lock:
            if self._stopped:
                return False
            if self._thread is not None and self._thread.is_alive():
                return False
            if not force and self._last_started is not None and now - self._last_started < self.interval:
                return False
            self._last_started = now
            self.status = "syncing"
            self._thread = threading.Thread(target=self._pull, daemon=True)
            self._thread.start()
            return True

    def _pull(self) -> None:
        try:
            result = self.runner(PULL_CMD, cwd=self.root, capture_output=True, text=True, timeout=120)
            if getattr(result, "returncode", 0) == 0:
                with self._lock:
                    self.status = "ok"
                    self.last_ok = time.time()
                    self.last_error = ""
            else:
                err = getattr(result, "stderr", "") or getattr(result, "stdout", "") or "git pull failed"
                with self._lock:
                    self.status = "error"
                    self.last_error = str(err).strip()
        except Exception as exc:  # noqa: BLE001 - never let the daemon die loudly
            with self._lock:
                self.status = "error"
                self.last_error = str(exc)
        finally:
            with self._lock:
                self._finished = True

    def tick(self, now: float) -> bool:
        """True when a pull finished since the last tick (caller should refresh)."""
        with self._lock:
            done = self._finished
            self._finished = False
        if self.enabled:
            self._launch(now)
        return done

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            thread = self._thread
        if thread is not None:
            thread.join(timeout=1.0)
