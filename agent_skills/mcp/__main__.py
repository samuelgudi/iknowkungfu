"""Entry point for the `iknowkungfu-mcp` CLI command.

Run as a subprocess by an MCP client (Claude Code, OpenClaw, etc.).
"""
import sys

from agent_skills.mcp.server import serve


def main() -> int:
    # Force UTF-8 on stdio so non-ASCII fields in skill metadata (descriptions
    # with em-dashes, accented author names, etc.) survive the round-trip.
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
