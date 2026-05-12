import subprocess
import sys


def test_help_lists_verbs():
    result = subprocess.run(
        [sys.executable, "-m", "agent_skills", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    for verb in (
        "search", "show", "install", "uninstall", "verify",
        "list", "update", "init", "submit", "issue", "deprecate", "yank",
    ):
        assert verb in result.stdout, f"verb '{verb}' missing from help"


def test_main_reconfigures_stdout_utf8_on_entry(monkeypatch, capsys):
    """cli.main must force UTF-8 on stdout/stderr at entry so Unicode glyphs
    survive on Windows consoles that default to CP1252. Regression test for
    Finding 2 of the 2026-05-12 walkthrough (★ in search output crashed)."""
    import io
    import sys
    from agent_skills import cli

    # Simulate a Windows CP1252 stdout that would reject U+2605.
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                                   write_through=True, line_buffering=True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                                   write_through=True, line_buffering=True)
    monkeypatch.setattr(sys, "stderr", fake_stderr)

    # Invoke with no-op verb that triggers parser help via missing args; we only
    # care that main() reaches its reconfigure logic without crashing.
    try:
        cli.main(["search", "anything"])
    except SystemExit:
        pass

    # After main() runs, stdout encoding must be utf-8 (or equivalent alias).
    enc = (sys.stdout.encoding or "").lower().replace("-", "")
    assert "utf8" in enc, f"expected UTF-8 stdout after cli.main; got {sys.stdout.encoding!r}"
    enc_err = (sys.stderr.encoding or "").lower().replace("-", "")
    assert "utf8" in enc_err, f"expected UTF-8 stderr after cli.main; got {sys.stderr.encoding!r}"


def test_cli_search_unicode_star_does_not_crash(tmp_path, monkeypatch, capsys):
    """End-to-end: search prints '★' in its top-match prefix. With CP1252
    stdout (Windows-cmd default), pre-fix this raised UnicodeEncodeError and
    exited 1. Post-fix it survives via UTF-8 reconfiguration."""
    import io
    import json as _json
    import sys
    from pathlib import Path

    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    (cache / "registry.json").write_text(_json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "test/example", "name": "example", "description": "find things",
            "version": "0.1.0", "status": "active",
            "author": {"name": "T", "github_login": "test", "github_id": 1},
            "category": "meta", "tags": ["search"], "platforms": ["windows"],
            "agent_compat": ["claude-code"], "license": "MIT",
            "install": {"claude-code": {"scope": "user"}},
            "requires": {"env_vars": [], "commands": []},
            "has_scripts": False,
            "versions": {"0.1.0": {"sha": "a" * 40, "released": "2026-05-11T00:00:00Z"}},
            "source": {"path": "skills/test/example", "content_hash": "sha256:0", "files": []},
        }],
    }))

    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                                   write_through=True, line_buffering=True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    from agent_skills.cli import main
    rc = main(["search", "find", "--agent", "claude-code"])
    assert rc == 0
    fake_stdout.flush()
    raw = fake_stdout.buffer.getvalue()
    # After fix, stdout has been reconfigured to UTF-8; the star is encodable.
    assert "★".encode("utf-8") in raw or b"\xe2\x98\x85" in raw


def test_detect_host_multi_host_message_includes_example(monkeypatch):
    """When multiple hosts are detected, the SystemExit message must give a
    ready-to-copy `--agent <name>` example and name the env var override.
    Finding 3 of the 2026-05-12 walkthrough — Samuel had both stacks installed
    and the bare `repr(['claude-code', 'hermes'])` was unfriendly."""
    import pytest
    from agent_skills.detect import detect_host
    from adapters.claude_code import ClaudeCodeAdapter
    from adapters.hermes import HermesAdapter

    monkeypatch.setattr(ClaudeCodeAdapter, "detect", lambda self: True)
    monkeypatch.setattr(HermesAdapter, "detect", lambda self: True)
    monkeypatch.delenv("AGENT_SKILLS_DEFAULT_AGENT", raising=False)

    with pytest.raises(SystemExit) as exc:
        detect_host()
    msg = str(exc.value)
    # Conversational text, not bare repr
    assert "claude-code" in msg and "hermes" in msg
    # Inline copy-pastable example
    assert "--agent claude-code" in msg or "--agent hermes" in msg
    # Env var override mentioned
    assert "AGENT_SKILLS_DEFAULT_AGENT" in msg
