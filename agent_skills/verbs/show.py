"""show verb — print detail on one skill."""
import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import detect_host, get_adapter


def find_skill(registry: dict, skill_id: str) -> dict | None:
    for s in registry.get("skills", []):
        if s["id"] == skill_id:
            return s
    return None


def is_installed(skill_id: str, agent: str) -> bool:
    try:
        adapter = get_adapter(agent)
    except Exception:
        return False
    for inst in adapter.list_installed():
        if inst.id == skill_id:
            return True
    return False


def run(args) -> int:
    registry = load_registry()
    if registry is None:
        print("Run `kfu update` first.", file=sys.stderr)
        return 1
    skill = find_skill(registry, args.id)
    if skill is None:
        print(f"Skill '{args.id}' not found in registry.", file=sys.stderr)
        return 1
    try:
        agent = detect_host(override=args.agent)
    except SystemExit:
        agent = None
    installed = is_installed(args.id, agent) if agent else False

    payload = {
        "id": skill["id"],
        "version": skill["version"],
        "status": skill["status"],
        "license": skill["license"],
        "author": skill["author"],
        "category": skill["category"],
        "tags": skill.get("tags", []),
        "platforms": skill.get("platforms", []),
        "agent_compat": skill.get("agent_compat", []),
        "files": skill.get("source", {}).get("files", []),
        "requires": skill.get("requires", {"env_vars": [], "commands": []}),
        "has_scripts": skill.get("has_scripts", False),
        "installed": installed,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"{skill['id']}  v{skill['version']}  ({skill['license']}, by {skill['author']['github_login']})")
    print()
    print(f"  {skill.get('description', '')}")
    print()
    print(f"  Category:  {skill['category']}")
    tags = skill.get("tags", [])
    tag_line = " ".join(f"#{t}" for t in tags) if tags else "—"
    print(f"  Tags:      {tag_line}")
    print(f"  Platforms: {', '.join(skill.get('platforms', [])) or '—'}")
    print(f"  Agents:    {', '.join(skill.get('agent_compat', [])) or '—'}")
    if skill.get("requires"):
        env = skill["requires"].get("env_vars", [])
        cmds = skill["requires"].get("commands", [])
        if env:
            print(f"  Env vars:  {', '.join(env)}")
        if cmds:
            print(f"  Commands:  {', '.join(cmds)}")
    print(f"  Files:")
    for f in skill.get("source", {}).get("files", []):
        print(f"    {f}")
    print()
    print(f"  Installed: {'yes (' + agent + ')' if installed else 'no'}")
    return 0
