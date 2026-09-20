"""Background HTTP poller for live mission status (stdlib only).

Fetches ``missions/status/*.json`` plus the plain mission list files from
GitHub (contents API + raw URLs) into a local ``.kingdom_cache/missions``
overlay so the UI stays live even where ``git pull`` is unavailable.
``DataAdapter`` reads the overlay first (see ``load_snapshot(..., overlay=)``).

Same lifecycle as :class:`kingdom.gitsync.GitSync`: ``start()`` kicks off a
daemon thread, ``tick(now)`` returns True once per finished fetch cycle, and
``stop()`` joins the thread. Errors land in ``last_error``; nothing raises.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

DEFAULT_REPO = "JojoTheWarrior/voloridge_hackmit"
STATUS_API = "https://api.github.com/repos/{repo}/contents/missions/status?ref={branch}"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{branch}/missions/{name}"
LIST_FILES = ("queue.txt", "in_progress.txt", "failed.txt")
_REMOTE_RE = re.compile(r"github\.com[:/]([^/:\s]+/[^/\s]+?)(?:\.git)?$")


def detect_repo(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True, timeout=10,
        )
        match = _REMOTE_RE.search(out.stdout.strip()) if out.returncode == 0 else None
        if match:
            return match.group(1)
    except (OSError, subprocess.SubprocessError):
        pass
    return DEFAULT_REPO


class HttpSync:
    def __init__(self, root: Path, repo: str = "", branch: str = "main", interval: float = 30.0,
                 enabled: bool = True, opener=urllib.request.urlopen, cache_dir: Optional[Path] = None):
        self.root = Path(root)
        self.repo = repo or detect_repo(self.root)
        self.branch = branch
        self.interval = float(interval)
        self.enabled = bool(enabled)
        self.opener = opener
        self.cache_dir = Path(cache_dir) if cache_dir is not None else self.root / ".kingdom_cache" / "missions"
        self.status: str = "ok" if self.enabled else "off"  # off | syncing | ok | error
        self.last_ok: Optional[float] = None
        self.last_error: str = ""
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._finished = False
        self._stopped = False
        self._last_started: Optional[float] = None

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> None:
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
            self._thread = threading.Thread(target=self._cycle_safe, daemon=True)
            self._thread.start()
            return True

    def tick(self, now: float) -> bool:
        """True when a fetch cycle finished since the last tick."""
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

    # -- fetch ---------------------------------------------------------------
    def _headers(self) -> dict:
        headers = {"User-Agent": "kingdom-dashboard", "Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _get(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers=self._headers())
        with self.opener(req, timeout=20) as resp:
            return resp.read()

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        tmp.rename(path)

    def _cycle(self) -> None:
        status_dir = self.cache_dir / "status"
        api_url = STATUS_API.format(repo=self.repo, branch=self.branch)
        entries = json.loads(self._get(api_url))
        names = set()
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("name") or "")
                url = entry.get("download_url")
                if entry.get("type") != "file" or not name.endswith(".json") or not url:
                    continue
                data = self._get(str(url))
                self._atomic_write(status_dir / name, data)
                names.add(name)
        try:
            cached = list(status_dir.glob("*.json"))
        except OSError:
            cached = []
        for old in cached:
            if old.name not in names:
                try:
                    old.unlink()
                except OSError:
                    pass
        for fname in LIST_FILES:
            url = RAW_URL.format(repo=self.repo, branch=self.branch, name=fname)
            target = self.cache_dir / fname
            try:
                data = self._get(url)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    try:
                        target.unlink()
                    except OSError:
                        pass
                    continue
                raise
            self._atomic_write(target, data)

    def _cycle_safe(self) -> None:
        try:
            self._cycle()
            with self._lock:
                self.status = "ok"
                self.last_ok = time.time()
                self.last_error = ""
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self.status = "error"
                self.last_error = str(exc)[:200]
        finally:
            with self._lock:
                self._finished = True
