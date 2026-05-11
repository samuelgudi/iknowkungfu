"""search verb."""
import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import detect_host
from clients.skill_discovery.match import rank


def run(args) -> int:
    registry = load_registry()
    if registry is None:
        print("Run `agent-skills update` first.", file=sys.stderr)
        return 1
    agent = detect_host(override=args.agent)
    candidates = rank(
        args.query if hasattr(args, "query") else " ".join(args.terms),
        registry,
        agent=agent,
        limit=getattr(args, "limit", 5),
    )
    if args.json:
        print(json.dumps({"candidates": candidates}, indent=2))
        return 0
    if not candidates:
        print("No skills match. Try `agent-skills list-categories` for ideas.")
        return 0
    for i, c in enumerate(candidates, 1):
        star = " ★" if i == 1 else "  "
        print(f"  {star} {i}  {c['id']:40s} v{c['version']}")
        print(f"       {c['description']}")
        tags = " ".join(f"#{t}" for t in c.get("tags", []))
        req = c.get("requires", {})
        req_part = ""
        if req.get("env_vars"):
            req_part = " · requires " + " + ".join(req["env_vars"])
        print(f"       {tags}{req_part}")
        print()
    return 0
