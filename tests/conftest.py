"""Shared pytest fixtures."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Patch HOME to a tmpdir for adapter tests."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


@pytest.fixture
def fake_gh(tmp_path, monkeypatch):
    """Install a fake `gh` shim on PATH. Returns the shim's invocation log path."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "gh.log"
    response_file = tmp_path / "gh.response"
    response_file.write_text(json.dumps({"id": 12345678, "login": "test-author"}))
    shim = bin_dir / ("gh.bat" if os.name == "nt" else "gh")
    if os.name == "nt":
        shim.write_text(
            f'@echo off\r\n'
            f'echo %* >> "{log_file}"\r\n'
            f'type "{response_file}"\r\n'
        )
    else:
        shim.write_text(
            f'#!/bin/sh\n'
            f'echo "$@" >> "{log_file}"\n'
            f'cat "{response_file}"\n'
        )
        os.chmod(shim, 0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    yield {"log": log_file, "response": response_file}


@pytest.fixture
def fake_registry_server(tmp_path):
    """Spin up an http.server serving a controlled registry.json. Yields the URL."""
    import http.server
    import socketserver
    import threading

    serve_dir = tmp_path / "registry"
    serve_dir.mkdir()
    handler = http.server.SimpleHTTPRequestHandler

    def serve():
        os.chdir(serve_dir)
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
            yield_url[0] = f"http://127.0.0.1:{httpd.server_address[1]}/registry.json"
            httpd.serve_forever()

    yield_url = [None]
    t = threading.Thread(target=serve, daemon=True)
    t.start()
    while yield_url[0] is None:
        pass
    yield {"url": yield_url[0], "dir": serve_dir}


@pytest.fixture
def good_fixture(request):
    """Yield a copy of a good/<name>/ fixture into tmp_path."""
    name = request.param
    src = FIXTURES_DIR / "good" / name
    return src


@pytest.fixture
def bad_fixture(request):
    name = request.param
    src = FIXTURES_DIR / "bad" / name
    return src
