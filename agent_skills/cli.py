"""agent-skills CLI verb dispatch."""
import argparse
import sys


VERBS = [
    "search", "show", "install", "uninstall", "verify",
    "list", "update", "init", "submit", "issue", "deprecate", "yank",
]


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent-skills", description="Agent-agnostic skill registry.")
    sub = p.add_subparsers(dest="verb", required=True)
    for v in VERBS:
        if v == "search":
            sp = sub.add_parser("search", help="Find skills by keyword")
            sp.add_argument("terms", nargs="+")
            sp.add_argument("--agent")
            sp.add_argument("--limit", type=int, default=5)
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "show":
            sp = sub.add_parser("show", help="Show details for one skill")
            sp.add_argument("id")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "install":
            sp = sub.add_parser("install", help="Install a skill (latest non-yanked by default)")
            sp.add_argument("spec", help="<id>[@version] or bare-slug")
            sp.add_argument("--agent")
            sp.add_argument("--scope", default="user", choices=["user", "project"])
            sp.add_argument("--allow-deprecated", action="store_true")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "uninstall":
            sp = sub.add_parser("uninstall", help="Remove an installed skill")
            sp.add_argument("id")
            sp.add_argument("--agent")
            sp.add_argument("--force", action="store_true", help="Remove even if local files have drifted")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "verify":
            sp = sub.add_parser("verify", help="Check an installed skill against the registry")
            sp.add_argument("id")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "list":
            sp = sub.add_parser("list", help="Show installed skills")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "update":
            sp = sub.add_parser("update", help="Refresh the local registry cache")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "init":
            sp = sub.add_parser("init", help="Scaffold meta.json interactively from SKILL.md")
            sp.add_argument("target")
            sp.add_argument("--yes", action="store_true")
        elif v == "submit":
            sp = sub.add_parser("submit", help="Submit a local skill as a PR")
            sp.add_argument("target")
            sp.add_argument("--yes", action="store_true")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
        else:
            sp = sub.add_parser(v, help=f"{v} verb")
            sp.add_argument("--agent", default=None)
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    p = make_parser()
    args = p.parse_args(argv)
    # Verb dispatch: each verb's run() function is in agent_skills/verbs/<verb>.py.
    # For Task 14, only verb registration matters; dispatch is added in Tasks 15-21 + 22-26.
    # Placeholder dispatch:
    if args.verb == "search":
        from agent_skills.verbs.search import run
        return run(args)
    if args.verb == "show":
        from agent_skills.verbs.show import run
        return run(args)
    if args.verb == "install":
        from agent_skills.verbs.install import run
        return run(args)
    if args.verb == "uninstall":
        from agent_skills.verbs.uninstall import run
        return run(args)
    if args.verb == "verify":
        from agent_skills.verbs.verify import run
        return run(args)
    if args.verb == "list":
        from agent_skills.verbs.list import run
        return run(args)
    if args.verb == "update":
        from agent_skills.verbs.update import run
        return run(args)
    if args.verb == "init":
        from agent_skills.verbs.init import run
        return run(args)
    if args.verb == "submit":
        from agent_skills.verbs.submit import run
        return run(args)
    # ... other verbs dispatched similarly; each verb's module added in its own task
    print(f"Verb '{args.verb}' not yet implemented (will be added in a later task).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
