"""list verb — show installed skills for the current/overridden host."""
from __future__ import annotations

import json
import sys

from agent_skills.detect import detect_host, get_adapter


def run(args) -> int:
    agent = detect_host(override=args.agent)
    adapter = get_adapter(agent)
    installed = adapter.list_installed()

    if args.json:
        payload = {
            "agent": agent,
            "installed": [
                {"id": i.id, "version": i.version, "target": str(i.target)}
                for i in installed
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    if not installed:
        print(f"No skills installed in {agent}.")
        return 0

    print(f"{len(installed)} skill(s) installed in {agent}:")
    for i in installed:
        print(f"  {i.id:40s} v{i.version}  → {i.target}")
    return 0
