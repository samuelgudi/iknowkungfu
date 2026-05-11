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
    # ... other verbs dispatched similarly; each verb's module added in its own task
    print(f"Verb '{args.verb}' not yet implemented (will be added in a later task).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
