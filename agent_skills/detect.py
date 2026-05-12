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
    raise SystemExit(
        "Multiple agent hosts detected: " + ", ".join(found) + ".\n"
        "Pick one with --agent, e.g.:\n"
        f"  agent-skills <verb> --agent {found[0]}\n"
        "Or set a default: export AGENT_SKILLS_DEFAULT_AGENT=" + found[0]
    )


def get_adapter(name: str):
    return ADAPTERS[name]()
