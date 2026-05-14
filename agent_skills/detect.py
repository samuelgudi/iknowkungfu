"""Host auto-detection."""
import os
from pathlib import Path

from adapters.claude_code import ClaudeCodeAdapter
from adapters.codex import CodexAdapter
from adapters.hermes import HermesAdapter
from adapters.opencode import OpenCodeAdapter
from adapters.openclaw import OpenClawAdapter
from adapters.pi import PiAdapter


ADAPTERS = {
    "claude-code": ClaudeCodeAdapter,
    "hermes": HermesAdapter,
    "codex": CodexAdapter,
    "opencode": OpenCodeAdapter,
    "pi": PiAdapter,
    "openclaw": OpenClawAdapter,
}


def detect_host(*, override: str | None = None) -> str:
    if override:
        if override not in ADAPTERS:
            raise SystemExit(f"unknown agent: {override}; expected one of {list(ADAPTERS)}")
        return override
    found = [name for name, cls in ADAPTERS.items() if cls().detect()]
    if not found:
        raise SystemExit(
            "No agent host detected. Pass --agent or install one of: "
            + ", ".join(ADAPTERS) + "."
        )
    if len(found) == 1:
        return found[0]
    pref = os.environ.get("IKNOWKUNGFU_DEFAULT_AGENT")
    if pref and pref in found:
        return pref
    raise SystemExit(
        "Multiple agent hosts detected: " + ", ".join(found) + ".\n"
        "Pick one with --agent, e.g.:\n"
        f"  kfu <verb> --agent {found[0]}\n"
        "Or set a default: export IKNOWKUNGFU_DEFAULT_AGENT=" + found[0]
    )


def get_adapter(name: str):
    return ADAPTERS[name]()


def find_install_hosts(skill_id: str, *, override: str | None = None) -> list[tuple]:
    """Resolve which host adapter(s) a skill should be inspected against.

    With an explicit override, returns just that host as `[(name, adapter)]` —
    the caller reports whether the skill is actually installed there. Without
    one, returns every detected host where the skill IS installed (empty if
    none). This answers "where is this skill?" rather than `detect_host`'s
    "which host am I?", which is the question `show` and `verify` need when
    no `--agent` is given.
    """
    if override:
        if override not in ADAPTERS:
            raise SystemExit(f"unknown agent: {override}; expected one of {list(ADAPTERS)}")
        return [(override, get_adapter(override))]
    hosts = []
    for name, cls in ADAPTERS.items():
        adapter = cls()
        if not adapter.detect():
            continue
        if any(inst.id == skill_id for inst in adapter.list_installed()):
            hosts.append((name, adapter))
    return hosts
