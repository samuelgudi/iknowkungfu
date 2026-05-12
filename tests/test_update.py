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

    cached = fake_home / ".cache/iknowkungfu/registry.json"
    assert cached.exists()
    assert json.loads(cached.read_text())["generated_at"] == "2026-05-11T00:00:00Z"


def test_refresh_rollback_guard_refuses_older(serve_dir, fake_home):
    """If fetched generated_at < cached generated_at, the write must be refused."""
    cache = fake_home / ".cache/iknowkungfu"
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


def test_refresh_rollback_guard_handles_mixed_tz_formats(serve_dir, fake_home):
    """Rollback guard must compare timestamps as datetimes, not raw strings.
    Bare string comparison treats "2026-05-12T10:43:59+02:00" as newer than
    "2026-05-12T08:44:15Z" even though UTC-08:44 > UTC-08:43. With a real-merge
    workflow (cache produced on a CEST dev box, fetched produced on GHA in UTC)
    this falsely triggered the rollback guard and blocked install."""
    cache = fake_home / ".cache/iknowkungfu"
    cache.mkdir(parents=True)
    # Cached: 08:43:59 UTC, expressed in CEST. Fetched: 08:44:15 UTC, expressed
    # with Z suffix. Fetched IS newer in absolute time.
    cached_reg = make_registry("2026-05-12T10:43:59+02:00")
    (cache / "registry.json").write_text(json.dumps(cached_reg))
    fetched_reg = make_registry("2026-05-12T08:44:15Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(fetched_reg))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc == 0, "Fetched is newer in UTC; refresh should succeed."
    assert json.loads((cache / "registry.json").read_text())["generated_at"] == "2026-05-12T08:44:15Z"


def test_refresh_rollback_guard_blocks_older_across_tz(serve_dir, fake_home):
    """Same as above but fetched IS older in UTC: must block."""
    cache = fake_home / ".cache/iknowkungfu"
    cache.mkdir(parents=True)
    # Cached: 09:00:00Z. Fetched: 10:00:00+02:00 = 08:00:00Z (older). Block.
    cached_reg = make_registry("2026-05-12T09:00:00Z")
    (cache / "registry.json").write_text(json.dumps(cached_reg))
    fetched_reg = make_registry("2026-05-12T10:00:00+02:00")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(fetched_reg))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc != 0, "Fetched is older in UTC; refresh must be blocked."
    assert json.loads((cache / "registry.json").read_text())["generated_at"] == "2026-05-12T09:00:00Z"


def test_refresh_atomic_write(serve_dir, fake_home):
    """No partial write on disk after a successful refresh."""
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc == 0

    cache_dir = fake_home / ".cache/iknowkungfu"
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

    cache = fake_home / ".cache/iknowkungfu"
    assert (cache / "yanks.json").exists()
    cached_yanks = json.loads((cache / "yanks.json").read_text())
    assert cached_yanks["yanks"][0]["id"] == "x/y"


def test_update_verb_invokes_refresh(serve_dir, fake_home, monkeypatch):
    """The verb-level run() calls refresh() and returns its exit code."""
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))
    monkeypatch.setenv("IKNOWKUNGFU_REGISTRY_URL", serve_dir["url"] + "/registry.json")
    # Skip the git clone in tests: we don't set REGISTRY_REPO so update.py only does the JSON pull
    monkeypatch.setenv("IKNOWKUNGFU_SKIP_REPO_SYNC", "1")
    (fake_home / ".claude").mkdir()

    from agent_skills.verbs.update import run
    class Args:
        agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    assert rc == 0
    assert (fake_home / ".cache/iknowkungfu/registry.json").exists()


def test_unsigned_warning_uses_proper_em_dash_after_utf8_fix(tmp_path, monkeypatch, capsys):
    """The unsigned-registry warning contains an em-dash (U+2014). After the
    Finding 2 UTF-8 reconfigure, the dash must reach stderr as proper UTF-8
    bytes (\\xe2\\x80\\x94), not '?' or a UnicodeEncodeError. Regression test
    for Finding 1 of the 2026-05-12 walkthrough."""
    import io
    import sys
    import json
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread

    payload = json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z", "skills": []
    }).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (stdlib API)
            if self.path.endswith("registry.json"):
                self.send_response(200); self.end_headers(); self.wfile.write(payload)
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *_a, **_k): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    t = Thread(target=server.serve_forever, daemon=True); t.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/registry.json"
        cache = tmp_path / "cache"
        monkeypatch.setattr("clients.skill_discovery.update._cache_dir", lambda: cache.mkdir(exist_ok=True) or cache)
        monkeypatch.setenv("IKNOWKUNGFU_SKIP_REPO_SYNC", "1")

        # Apply the same reconfigure cli.main does, to mirror real CLI usage.
        from agent_skills.cli import _force_utf8_streams
        _force_utf8_streams()

        from clients.skill_discovery.update import refresh
        rc = refresh(registry_url=url)
        assert rc == 0
    finally:
        server.shutdown()

    captured = capsys.readouterr()
    # Em-dash (U+2014) must appear in stderr message — not '?' (lossy replace)
    # and not omitted (raised exception).
    assert "—" in captured.err


# ─── Regression: registry-repo clone MUST NOT be shallow ──────────────────
#
# Before 0.1.3, _sync_registry_repo used `git clone --depth=1` and
# `git fetch --depth=1`. The depth=1 clone is incompatible with
# install_skill, which `git archive`s a version-pinned SHA that may
# predate origin/main's tip. The pinned SHA's tree isn't in a shallow
# clone, so git archive returns exit 128 and install fails.
# These tests pin the contract: no --depth flag may appear in the git
# argv produced by _sync_registry_repo.

class _CapturingRun:
    """Drop-in replacement for subprocess.run that records argv lists."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, argv, *args, **kwargs):
        self.calls.append(list(argv))

        class _Done:
            returncode = 0
            stdout = b""
            stderr = b""

        return _Done()


def test_sync_registry_repo_clone_is_full_history(tmp_path, monkeypatch):
    from clients.skill_discovery import update as upd

    capture = _CapturingRun()
    monkeypatch.setattr(upd.subprocess, "run", capture)

    # Fresh dest → triggers the clone branch.
    upd._sync_registry_repo("https://example.test/repo.git", tmp_path / "fresh")

    assert capture.calls, "expected at least one git invocation"
    for argv in capture.calls:
        assert "--depth=1" not in argv, (
            f"shallow clone forbidden — install_skill needs full history. "
            f"Offending argv: {argv}"
        )
        assert "--depth" not in argv, (
            f"any --depth limit forbidden. Offending argv: {argv}"
        )
    # The clone command specifically must look like `git clone <url> <dest>`.
    clone_calls = [a for a in capture.calls if "clone" in a]
    assert clone_calls, "expected a `git clone` invocation"


def test_sync_registry_repo_fetch_is_full_history(tmp_path, monkeypatch):
    from clients.skill_discovery import update as upd

    dest = tmp_path / "existing"
    (dest / ".git").mkdir(parents=True)  # pretend the repo is already cloned

    capture = _CapturingRun()
    monkeypatch.setattr(upd.subprocess, "run", capture)

    upd._sync_registry_repo("https://example.test/repo.git", dest)

    assert capture.calls, "expected git fetch + reset invocations"
    for argv in capture.calls:
        assert "--depth=1" not in argv, (
            f"shallow fetch forbidden — install_skill needs full history. "
            f"Offending argv: {argv}"
        )
        assert "--depth" not in argv, (
            f"any --depth limit forbidden. Offending argv: {argv}"
        )
    # Tags must travel along so the install verb can resolve `v{ver}-<slug>`.
    fetch_calls = [a for a in capture.calls if "fetch" in a]
    assert fetch_calls, "expected a `git fetch` invocation"
    assert any("--tags" in a for a in fetch_calls), (
        "fetch must include --tags so version tags reach the local clone"
    )
