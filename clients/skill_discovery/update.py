"""Registry refresh — HTTPS fetch, rollback guard, atomic write."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path


DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/samuelgudi/agent-skills/main/registry.json"
DEFAULT_REGISTRY_REPO = "https://github.com/samuelgudi/agent-skills.git"


def _cache_dir() -> Path:
    d = Path.home() / ".cache/agent-skills"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _http_fetch(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "agent-skills/0.1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _atomic_write(target: Path, data: bytes) -> None:
    """Write to a sibling tmp file, fsync, rename onto target."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=str(target.parent), delete=False,
                                     prefix=f".{target.name}.tmp.") as tf:
        tf.write(data)
        tf.flush()
        os.fsync(tf.fileno())
        tmp_path = Path(tf.name)
    os.replace(tmp_path, target)


def _sync_registry_repo(repo_url: str, dest: Path) -> None:
    if (dest / ".git").exists():
        subprocess.run(["git", "-C", str(dest), "fetch", "--depth=1", "origin", "main"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(dest), "reset", "--hard", "FETCH_HEAD"],
                       check=True, capture_output=True)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth=1", repo_url, str(dest)],
                   check=True, capture_output=True)


def refresh(registry_url: str | None = None, *, repo_url: str | None = None) -> int:
    """Fetch registry.json + yanks.json, verify rollback, write atomically.
    Sync registry-repo clone (skipped if AGENT_SKILLS_SKIP_REPO_SYNC=1).
    Returns 0 on success, 1 on error/rollback."""
    cache = _cache_dir()
    url = registry_url or os.environ.get("AGENT_SKILLS_REGISTRY_URL", DEFAULT_REGISTRY_URL)

    try:
        reg_bytes = _http_fetch(url)
    except urllib.error.URLError as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        return 1

    try:
        fetched = json.loads(reg_bytes)
    except json.JSONDecodeError as e:
        print(f"Fetched registry is not valid JSON: {e}", file=sys.stderr)
        return 1

    cached_path = cache / "registry.json"
    if cached_path.exists():
        try:
            cached = json.loads(cached_path.read_text(encoding="utf-8"))
            if fetched.get("generated_at", "") < cached.get("generated_at", ""):
                print(
                    f"Rollback guard: fetched generated_at {fetched.get('generated_at')} "
                    f"< cached {cached.get('generated_at')}. Refusing to overwrite.",
                    file=sys.stderr,
                )
                return 1
        except (json.JSONDecodeError, OSError):
            pass  # Cached file corrupt — treat as missing.

    _atomic_write(cached_path, reg_bytes)

    # Optional sig — warn if missing
    sig_url = url + ".sig"
    try:
        sig_bytes = _http_fetch(sig_url, timeout=5.0)
        _atomic_write(cache / "registry.json.sig", sig_bytes)
    except urllib.error.URLError:
        print("Warning: registry.json.sig not found — running unsigned.", file=sys.stderr)

    # yanks.json — sibling to registry
    yanks_url = url.rsplit("/", 1)[0] + "/yanks.json"
    try:
        yanks_bytes = _http_fetch(yanks_url, timeout=10.0)
        _atomic_write(cache / "yanks.json", yanks_bytes)
    except urllib.error.URLError:
        pass  # yanks.json optional

    # Sync the registry-repo clone (needed for install's git archive step)
    if os.environ.get("AGENT_SKILLS_SKIP_REPO_SYNC") != "1":
        repo = repo_url or os.environ.get("AGENT_SKILLS_REGISTRY_REPO", DEFAULT_REGISTRY_REPO)
        repo_cache = cache / "registry-repo"
        try:
            _sync_registry_repo(repo, repo_cache)
        except subprocess.CalledProcessError as e:
            print(f"Warning: registry-repo sync failed: {e}. install verb may not work.",
                  file=sys.stderr)

    return 0
