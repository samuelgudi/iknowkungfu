"""show verb — print detail on one skill."""
import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import find_install_hosts


def find_skill(registry: dict, skill_id: str) -> dict | None:
    for s in registry.get("skills", []):
        if s["id"] == skill_id:
            return s
    return None


def run(args) -> int:
    registry = load_registry()
    if registry is None:
        print("Run `kfu update` first.", file=sys.stderr)
        return 1
    skill = find_skill(registry, args.id)
    if skill is None:
        print(f"Skill '{args.id}' not found in registry.", file=sys.stderr)
        return 1
    # Where is the skill installed? With --agent, check that host; without,
    # check every detected host. Answers "where is this skill?" rather than
    # "which host am I?" — the latter wrongly reported "Installed: no" on
    # multi-host setups.
    try:
        hosts = find_install_hosts(args.id, override=args.agent)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 1
    if args.agent:
        _, adapter = hosts[0]
        installed_in = (
            [args.agent]
            if any(i.id == args.id for i in adapter.list_installed())
            else []
        )
    else:
        installed_in = [name for name, _ in hosts]
    installed = bool(installed_in)

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
        "installed_in": installed_in,
    }
    # `origin` (ADR-002) is present only on imported skills.
    origin = skill.get("origin")
    if origin:
        payload["origin"] = origin

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    if origin:
        byline = (
            f"curated by {skill['author']['github_login']}, "
            f"originally by {origin['author_name']}"
        )
    else:
        byline = f"by {skill['author']['github_login']}"
    print(f"{skill['id']}  v{skill['version']}  ({skill['license']}, {byline})")
    print()
    print(f"  {skill.get('description', '')}")
    print()
    print(f"  Category:  {skill['category']}")
    tags = skill.get("tags", [])
    tag_line = " ".join(f"#{t}" for t in tags) if tags else "—"
    print(f"  Tags:      {tag_line}")
    print(f"  Platforms: {', '.join(skill.get('platforms', [])) or '—'}")
    print(f"  Agents:    {', '.join(skill.get('agent_compat', [])) or '—'}")
    if origin:
        url = f" ({origin['author_url']})" if origin.get("author_url") else ""
        print(f"  Origin:    {origin['repo']} @ {origin['ref']}")
        print(f"             originally by {origin['author_name']}{url}, "
              f"imported {origin['imported_at']}")
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
    if installed:
        print(f"  Installed: yes ({', '.join(installed_in)})")
    else:
        print(f"  Installed: no")
        print(f"    Run: kfu install {skill['id']}")
    return 0
