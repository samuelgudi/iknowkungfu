"""verify verb — check installed skill against registry."""
from __future__ import annotations

import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import detect_host, get_adapter
from adapters._base import read_marker


def run(args) -> int:
    agent = detect_host(override=args.agent)
    adapter = get_adapter(agent)
    registry = load_registry()
    if registry is None:
        print("No registry cache. Run `kfu update`.", file=sys.stderr)
        return 1

    skill = next((s for s in registry["skills"] if s["id"] == args.id), None)
    if skill is None:
        print(f"{args.id} not found in registry.", file=sys.stderr)
        return 1

    # Determine installed version to look up the right yanked flag
    yanked = False
    yank_reason = None
    registry_hash = skill.get("source", {}).get("content_hash", "")

    # Try to read the installed version from the marker so we can check the right yank entry
    for inst in adapter.list_installed():
        if inst.id == args.id:
            marker = read_marker(inst.target)
            installed_ver = marker.get("version") if marker else None
            if installed_ver and installed_ver in skill.get("versions", {}):
                v = skill["versions"][installed_ver]
                yanked = v.get("yanked", False)
                yank_reason = v.get("yank_reason")
            break

    vr = adapter.verify(args.id, registry_hash=registry_hash, yanked=yanked, yank_reason=yank_reason)

    # Exit-code matrix:
    #   Without --json:  0 = clean ; 1 = any non-clean status.
    #   With    --json:  0 = verify ran (status in payload) ; non-zero only on
    #                    hard errors (missing registry, unknown agent, etc.).
    #                    The JSON payload IS the machine-readable answer in all
    #                    non-error cases. Finding 6 of the 2026-05-12 walkthrough.
    if args.json:
        print(json.dumps({"id": args.id, "status": vr.status, "message": vr.message}, indent=2))
        return 0

    print(f"{args.id}: {vr.status.upper()}")
    print(f"  {vr.message}")
    return 0 if vr.status == "clean" else 1
