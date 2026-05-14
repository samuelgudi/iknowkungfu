"""verify verb — check installed skill against registry."""
from __future__ import annotations

import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import find_install_hosts
from adapters._base import read_marker


def _verify_one(adapter, skill: dict, skill_id: str):
    """Run the adapter's verify for one host, resolving the right yank flag
    from the installed version's marker."""
    yanked = False
    yank_reason = None
    registry_hash = skill.get("source", {}).get("content_hash", "")
    for inst in adapter.list_installed():
        if inst.id == skill_id:
            marker = read_marker(inst.target)
            installed_ver = marker.get("version") if marker else None
            if installed_ver and installed_ver in skill.get("versions", {}):
                v = skill["versions"][installed_ver]
                yanked = v.get("yanked", False)
                yank_reason = v.get("yank_reason")
            break
    return adapter.verify(
        skill_id, registry_hash=registry_hash, yanked=yanked, yank_reason=yank_reason
    )


def run(args) -> int:
    registry = load_registry()
    if registry is None:
        print("No registry cache. Run `kfu update`.", file=sys.stderr)
        return 1

    skill = next((s for s in registry["skills"] if s["id"] == args.id), None)
    if skill is None:
        print(f"{args.id} not found in registry.", file=sys.stderr)
        return 1

    # Resolve where to verify. With --agent, that host. Without, every detected
    # host where the skill is installed — so a multi-host setup no longer fails
    # with a "pick one with --agent" error when the skill is plainly installed
    # in exactly one of them.
    try:
        hosts = find_install_hosts(args.id, override=args.agent)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 1

    if not hosts:
        # No --agent given, and not installed in any detected host.
        msg = f"{args.id} is not installed in any detected host."
        if args.json:
            print(json.dumps(
                {"id": args.id, "status": "not_installed", "message": msg}, indent=2
            ))
            return 0
        print(msg, file=sys.stderr)
        return 1

    results = [(name, _verify_one(adapter, skill, args.id)) for name, adapter in hosts]

    # Exit-code matrix:
    #   Without --json:  0 = every host clean ; 1 = any non-clean status.
    #   With    --json:  0 = verify ran (status in payload) ; non-zero only on
    #                    hard errors (missing registry, unknown agent). The
    #                    JSON payload IS the machine-readable answer otherwise.
    if args.json:
        # One host (explicit --agent, or exactly one host with it installed):
        # keep the original {id, status, message} shape. Multiple: a list.
        if len(results) == 1:
            _, vr = results[0]
            print(json.dumps(
                {"id": args.id, "status": vr.status, "message": vr.message}, indent=2
            ))
        else:
            print(json.dumps({
                "id": args.id,
                "hosts": [
                    {"agent": name, "status": vr.status, "message": vr.message}
                    for name, vr in results
                ],
            }, indent=2))
        return 0

    multi = len(results) > 1
    all_clean = True
    for name, vr in results:
        prefix = f"[{name}] " if multi else ""
        print(f"{prefix}{args.id}: {vr.status.upper()}")
        print(f"  {vr.message}")
        if vr.status != "clean":
            all_clean = False
    return 0 if all_clean else 1
