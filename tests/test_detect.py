"""Tests for host auto-detection. Locks the contract:
- All declared agents are registered in ADAPTERS
- detect_host honours --agent override
- Multi-host detection falls back to AGENT_SKILLS_DEFAULT_AGENT env var
"""
from pathlib import Path

import pytest

from agent_skills.detect import ADAPTERS, detect_host, get_adapter
from agent_skills.verbs.init import AGENTS


def test_adapters_match_init_agents_list():
    """agent_skills/verbs/init.py advertises the agent list; ADAPTERS must mirror
    that set. If a future verb adds an agent without an adapter, the registry
    can surface skills that have nowhere to install — fail loudly here instead."""
    assert set(ADAPTERS) == set(AGENTS), (
        f"ADAPTERS={set(ADAPTERS)} but init.AGENTS={set(AGENTS)}. "
        "These two must stay in sync."
    )


def test_override_returns_named_agent():
    assert detect_host(override="codex") == "codex"
    assert detect_host(override="opencode") == "opencode"


def test_override_rejects_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with pytest.raises(SystemExit, match="unknown agent"):
        detect_host(override="copilot")


def test_no_host_detected_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("AGENT_SKILLS_DEFAULT_AGENT", raising=False)
    with pytest.raises(SystemExit, match="No agent host detected"):
        detect_host()


def test_single_host_detected_returns_it(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("AGENT_SKILLS_DEFAULT_AGENT", raising=False)
    (tmp_path / ".codex").mkdir()
    assert detect_host() == "codex"


def test_multi_host_without_default_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("AGENT_SKILLS_DEFAULT_AGENT", raising=False)
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".config/opencode").mkdir(parents=True)
    with pytest.raises(SystemExit, match="Multiple agent hosts detected"):
        detect_host()


def test_multi_host_with_default_returns_default(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".config/opencode").mkdir(parents=True)
    monkeypatch.setenv("AGENT_SKILLS_DEFAULT_AGENT", "opencode")
    assert detect_host() == "opencode"


def test_get_adapter_returns_instance_for_each_agent():
    for name in ADAPTERS:
        a = get_adapter(name)
        assert a.name == name, f"{name} adapter's .name attribute mismatches registry key"
