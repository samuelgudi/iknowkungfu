"""I Know Kung Fu CLI verb dispatch."""
import argparse
import sys


def _force_utf8_streams() -> None:
    """Force sys.stdout/stderr to UTF-8 at CLI entry. Windows consoles default
    to CP1252 (or similar legacy code page), which can't encode common output
    glyphs (★, em-dash). Reconfiguring at the entrypoint costs nothing on POSIX
    (already UTF-8) and prevents UnicodeEncodeError tracebacks on Windows.
    Uses errors='replace' on stderr so warning messages never bubble a second
    fault if a truly unmappable char slips through."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        # Some test environments wrap streams in non-reconfigurable BufferedIO;
        # guard with hasattr so we degrade gracefully rather than blow up.
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            # Stream not text-mode or already detached; nothing to do.
            pass


VERBS = [
    "search", "show", "install", "uninstall", "verify",
    "list", "update", "init", "submit", "issue", "deprecate", "yank",
]


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kfu", description="Agent-agnostic skill registry.")
    sub = p.add_subparsers(dest="verb", required=True)
    for v in VERBS:
        if v == "search":
            sp = sub.add_parser(
                "search",
                help="Find skills using the query DSL (tag:, agent:, version:>=, etc.)",
            )
            # `terms` is now the raw query DSL string. nargs='*' so callers can
            # pass zero positional args (filter-only queries like `--tag rust`).
            sp.add_argument("terms", nargs="*", default=[])
            # Deprecated flags retained for one release cycle. Translated to
            # DSL prefixes internally and emit a stderr warning.
            sp.add_argument("--agent", help="DEPRECATED: use 'agent:X' in the query")
            sp.add_argument("--category", help="DEPRECATED: use 'category:X' in the query")
            sp.add_argument("--tag", help="DEPRECATED: use 'tag:X' in the query")
            # Pagination + filters.
            sp.add_argument("--limit", type=int, default=5)
            sp.add_argument("--offset", type=int, default=0)
            sp.add_argument(
                "--include-deprecated",
                action="store_true",
                help="Include skills with status:deprecated",
            )
            # Output formats.
            sp.add_argument("--json", action="store_true")
            sp.add_argument(
                "--ndjson", action="store_true", help="Newline-delimited JSON"
            )
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
        elif v == "issue":
            sp = sub.add_parser("issue", help="Open an issue about a skill")
            sp.add_argument("id")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "deprecate":
            sp = sub.add_parser("deprecate", help="Propose deprecation of a skill")
            sp.add_argument("id")
            sp.add_argument("--in-favor-of", required=True, dest="in_favor_of",
                            help="Successor skill id (<author>/<slug>)")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        elif v == "yank":
            sp = sub.add_parser("yank", help="Hard-yank a compromised version (no install override)")
            sp.add_argument("spec", help="<id>@<version>")
            sp.add_argument("--reason", required=True, help="Concrete reason (compromise summary)")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
        else:
            sp = sub.add_parser(v, help=f"{v} verb")
            sp.add_argument("--agent", default=None)
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    _force_utf8_streams()
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
    if args.verb == "issue":
        from agent_skills.verbs.issue import run
        return run(args)
    if args.verb == "deprecate":
        from agent_skills.verbs.deprecate import run
        return run(args)
    if args.verb == "yank":
        from agent_skills.verbs.yank import run
        return run(args)
    # Argparse with required=True on the subparser rejects unknown verbs at
    # parse time, so this point is unreachable. The explicit return keeps the
    # type checker happy.
    return 2


if __name__ == "__main__":
    sys.exit(main())
