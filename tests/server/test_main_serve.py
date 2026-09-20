"""Tests for the `serve` subcommand in main.py."""
from __future__ import annotations

import sys

import pytest

import main as cli
from server import app as server_app


@pytest.fixture
def served(monkeypatch):
    calls = []
    monkeypatch.setattr(server_app, "serve", lambda **kwargs: calls.append(kwargs))
    return calls


def test_serve_defaults(monkeypatch, served):
    monkeypatch.setattr(sys, "argv", ["main.py", "serve"])
    cli.main()
    assert served == [{"host": "127.0.0.1", "port": 8030, "db": ".kingdom/kingdom.db"}]


def test_serve_options(monkeypatch, served, tmp_path):
    db = str(tmp_path / "other.db")
    monkeypatch.setattr(sys, "argv", ["main.py", "serve", "--port", "8031", "--host", "0.0.0.0", "--db", db])
    cli.main()
    assert served == [{"host": "0.0.0.0", "port": 8031, "db": db}]


def test_serve_rejects_a_non_numeric_port(monkeypatch, served):
    monkeypatch.setattr(sys, "argv", ["main.py", "serve", "--port", "http"])
    with pytest.raises(SystemExit):
        cli.main()
    assert served == []
