"""list verb — show installed skills for the current/overridden host."""
from __future__ import annotations

import json

from agent_skills.detect import ADAPTERS, detect_host, get_adapter


def _list_one(agent: str) -> list:
    return get_adapter(agent).list_installed()


def run(args) -> int:
    if args.agent:
        agents = [detect_host(override=args.agent)]
    else:
        # `list` is read-only — when multiple hosts are detected, show them
        # all rather than forcing the user to pick. install/verify still
        # require disambiguation; list does not.
        detected = [name for name, cls in ADAPTERS.items() if cls().detect()]
        if not detected:
            print("No agent host detected. Pass --agent or install one of: "
                  + ", ".join(ADAPTERS) + ".")
            return 0
        agents = detected

    sections = [(a, _list_one(a)) for a in agents]

    if args.json:
        # Single-host (explicit --agent OR auto-detect found one): keep the
        # v0.1.2 JSON shape {agent, installed:[...]} for back-compat.
        # Multi-host (auto-detect found 2+ without override): use the new
        # shape {agents:[{agent, installed:[...]}, ...]}.
        if len(sections) == 1:
            agent, installed = sections[0]
            payload = {
                "agent": agent,
                "installed": [
                    {"id": i.id, "version": i.version, "target": str(i.target)}
                    for i in installed
                ],
            }
        else:
            payload = {
                "agents": [
                    {
                        "agent": agent,
                        "installed": [
                            {"id": i.id, "version": i.version, "target": str(i.target)}
                            for i in installed
                        ],
                    }
                    for agent, installed in sections
                ],
            }
        print(json.dumps(payload, indent=2))
        return 0

    multi = len(sections) > 1
    for agent, installed in sections:
        if multi:
            print(f"=== {agent} ===")
        if not installed:
            print(f"No skills installed in {agent}.")
        else:
            print(f"{len(installed)} skill(s) installed in {agent}:")
            for i in installed:
                print(f"  {i.id:40s} v{i.version}  → {i.target}")
        if multi:
            print()
    return 0
