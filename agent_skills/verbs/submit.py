"""submit verb — thin wrapper around clients.skill_contribution.submit."""
from pathlib import Path

from clients.skill_contribution.submit import submit_skill


def run(args) -> int:
    repo = Path.cwd()
    result = submit_skill(Path(args.target), repo, yes=getattr(args, "yes", False))
    if not result.success:
        import sys
        print(f"submit failed: {result.error}", file=sys.stderr)
        return 1
    print(f"Submitted: {result.pr_url}")
    return 0
