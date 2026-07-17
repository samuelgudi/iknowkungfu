"""uninstall verb."""
from __future__ import annotations

import json
import sys

from adapters._base import split_skill_id
from agent_skills.cache import load_registry
from agent_skills.detect import detect_host, get_adapter


def run(args) -> int:
    try:
        split_skill_id(args.id)
    except ValueError as e:
        print(f"Uninstall failed: {e}", file=sys.stderr)
        return 1
    agent = detect_host(override=args.agent)
    adapter = get_adapter(agent)

    registry = load_registry()
    registry_hash = ""
    if registry:
        for s in registry.get("skills", []):
            if s["id"] == args.id:
                registry_hash = s.get("source", {}).get("content_hash", "")
                break

    if not getattr(args, "force", False):
        vr = adapter.verify(args.id, registry_hash=registry_hash, yanked=False, yank_reason=None)
        if vr.status == "drift":
            print(f"Drift detected: {vr.message}", file=sys.stderr)
            print("Refusing to uninstall a modified skill. Use --force to override.", file=sys.stderr)
            return 1
        if vr.status == "not_installed":
            print(f"{args.id} is not installed in {agent}.", file=sys.stderr)
            return 1

    result = adapter.uninstall(args.id)
    if not result.success:
        print(f"Uninstall failed: {result.error}", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        print(json.dumps({"uninstalled": True, "id": args.id, "target": str(result.target)}, indent=2))
    else:
        print(f"Removed {result.target}")
    return 0
