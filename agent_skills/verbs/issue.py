"""issue verb — interactive wizard → gh issue create."""
from __future__ import annotations

import subprocess
import sys


ISSUE_TYPES = {
    "1": ("bug", "Bug"),
    "2": ("feature", "Feature request"),
    "3": ("docs", "Documentation"),
    "4": ("security", "Security concern"),
}


def _prompt(msg: str, *, default: str | None = None, allow_empty: bool = False,
            prompt_fn=input) -> str:
    display = f"{msg} [{default}]: " if default is not None else f"{msg}: "
    while True:
        val = prompt_fn(display).strip()
        if not val and default is not None:
            return default
        if val or allow_empty:
            return val


def _find_gh() -> str:
    """Return the resolved path to a gh executable (favours .bat/.cmd shims when on PATH first)."""
    import shutil
    found = shutil.which("gh")
    if found:
        return found
    raise SystemExit("gh CLI not found on PATH. Install GitHub CLI: https://cli.github.com/")


def run(args, *, prompt_fn=input) -> int:
    skill_id = args.id
    print(f"Opening an issue for skill: {skill_id}")
    print()
    print("Issue type:")
    for k, (_slug, label) in ISSUE_TYPES.items():
        print(f"  [{k}] {label}")
    while True:
        choice = _prompt("Selection (1-4)", prompt_fn=prompt_fn)
        if choice in ISSUE_TYPES:
            issue_slug, issue_label = ISSUE_TYPES[choice]
            break
        print(f"  Invalid choice: {choice}")

    title = _prompt("Title (concise summary)", prompt_fn=prompt_fn)
    context = _prompt("Context (1-3 sentences; what triggered this)", prompt_fn=prompt_fn)
    proposal = _prompt("Proposed change (what you'd like to see)", prompt_fn=prompt_fn)
    will_impl = _prompt("Will you implement this yourself? (y/n)", default="n", prompt_fn=prompt_fn).lower().startswith("y")

    body = (
        f"**Skill**: `{skill_id}`\n"
        f"**Type**: {issue_label}\n"
        f"**Will implement myself**: {'yes' if will_impl else 'no'}\n\n"
        f"### Context\n{context}\n\n"
        f"### Proposed change\n{proposal}\n"
    )
    full_title = f"[{issue_slug}] {skill_id}: {title}"

    gh = _find_gh()
    result = subprocess.run(
        [gh, "issue", "create", "--title", full_title, "--body", body],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"gh issue create failed: {result.stderr}", file=sys.stderr)
        return 1
    print(f"Issue opened: {result.stdout.strip()}")
    return 0
