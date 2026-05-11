"""Host auto-detection."""
import os
from pathlib import Path

from adapters.claude_code import ClaudeCodeAdapter
from adapters.hermes import HermesAdapter


ADAPTERS = {"claude-code": ClaudeCodeAdapter, "hermes": HermesAdapter}


def detect_host(*, override: str | None = None) -> str:
    if override:
        if override not in ADAPTERS:
            raise SystemExit(f"unknown agent: {override}; expected one of {list(ADAPTERS)}")
        return override
    found = [name for name, cls in ADAPTERS.items() if cls().detect()]
    if not found:
        raise SystemExit("No agent host detected. Pass --agent or install Claude Code / Hermes.")
    if len(found) == 1:
        return found[0]
    pref = os.environ.get("AGENT_SKILLS_DEFAULT_AGENT")
    if pref and pref in found:
        return pref
    raise SystemExit(f"Multiple hosts detected ({found}). Set AGENT_SKILLS_DEFAULT_AGENT or pass --agent.")


def get_adapter(name: str):
    return ADAPTERS[name]()
