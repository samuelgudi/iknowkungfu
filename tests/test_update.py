"""Tests for the update verb / refresh() routine."""
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest


@pytest.fixture
def serve_dir(tmp_path):
    """Spin up http.server serving files from a tmpdir; yield the URL base."""
    serve = tmp_path / "serve"
    serve.mkdir()

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve), **kwargs)

    httpd = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield {"dir": serve, "url": f"http://127.0.0.1:{port}"}
    httpd.shutdown()


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


def make_registry(generated_at, skills=None):
    return {
        "schema_version": 2,
        "generated_at": generated_at,
        "skills": skills or [],
    }


def test_refresh_writes_registry(serve_dir, fake_home):
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))
    (serve_dir["dir"] / "yanks.json").write_text(json.dumps({"yanks": []}))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc == 0

    cached = fake_home / ".cache/agent-skills/registry.json"
    assert cached.exists()
    assert json.loads(cached.read_text())["generated_at"] == "2026-05-11T00:00:00Z"


def test_refresh_rollback_guard_refuses_older(serve_dir, fake_home):
    """If fetched generated_at < cached generated_at, the write must be refused."""
    cache = fake_home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    cached_reg = make_registry("2026-05-15T00:00:00Z")
    (cache / "registry.json").write_text(json.dumps(cached_reg))

    fetched_reg = make_registry("2026-05-10T00:00:00Z")  # OLDER
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(fetched_reg))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc != 0

    # The cached registry must remain the newer one
    assert json.loads((cache / "registry.json").read_text())["generated_at"] == "2026-05-15T00:00:00Z"


def test_refresh_atomic_write(serve_dir, fake_home):
    """No partial write on disk after a successful refresh."""
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc == 0

    cache_dir = fake_home / ".cache/agent-skills"
    leftovers = [p for p in cache_dir.iterdir() if p.name.startswith(".registry.json.tmp")]
    assert leftovers == []


def test_refresh_yanks_when_present(serve_dir, fake_home):
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))
    yanks = {"yanks": [{"id": "x/y", "version": "0.1.0", "reason": "test", "yanked_at": "2026-05-11T00:00:00Z", "yanked_by": "ci"}]}
    (serve_dir["dir"] / "yanks.json").write_text(json.dumps(yanks))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc == 0

    cache = fake_home / ".cache/agent-skills"
    assert (cache / "yanks.json").exists()
    cached_yanks = json.loads((cache / "yanks.json").read_text())
    assert cached_yanks["yanks"][0]["id"] == "x/y"


def test_update_verb_invokes_refresh(serve_dir, fake_home, monkeypatch):
    """The verb-level run() calls refresh() and returns its exit code."""
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))
    monkeypatch.setenv("AGENT_SKILLS_REGISTRY_URL", serve_dir["url"] + "/registry.json")
    # Skip the git clone in tests: we don't set REGISTRY_REPO so update.py only does the JSON pull
    monkeypatch.setenv("AGENT_SKILLS_SKIP_REPO_SYNC", "1")
    (fake_home / ".claude").mkdir()

    from agent_skills.verbs.update import run
    class Args:
        agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    assert rc == 0
    assert (fake_home / ".cache/agent-skills/registry.json").exists()
