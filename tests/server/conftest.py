from __future__ import annotations

import pytest
import requests


def pytest_collection_modifyitems(config, items):
    if "live" in (config.getoption("-m") or ""):
        return
    skip = pytest.mark.skip(reason="live Devin test; run with -m live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _no_real_devin(request, monkeypatch):
    """Keep the suite offline: hide the key from .env and refuse real HTTP."""
    if "live" in request.keywords:
        return
    monkeypatch.delenv("DEVIN_API_KEY", raising=False)
    monkeypatch.delenv("KINGDOM_FAKE_DEVIN", raising=False)

    def refuse(self, method, url, *args, **kwargs):
        raise AssertionError(f"unexpected real HTTP request: {method} {url}")

    monkeypatch.setattr(requests.sessions.Session, "request", refuse)
