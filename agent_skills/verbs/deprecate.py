"""deprecate verb — soft obsolescence: status=deprecated + dir move skills/ -> archive/."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _find_gh() -> str:
    import shutil as _sh
    found = _sh.which("gh")
    if found:
        return found
    raise SystemExit("gh CLI not found on PATH.")


def deprecate(repo: Path, skill_id: str, superseded_by: str) -> tuple[bool, str | None]:
    """Apply the deprecation locally and open a PR. Returns (success, pr_url_or_error)."""
    repo = Path(repo).resolve()
    if "/" not in skill_id:
        return False, f"invalid skill id: {skill_id!r}"
    author, slug = skill_id.split("/", 1)
    src = repo / "skills" / author / slug
    if not src.exists():
        return False, f"skill not found at {src}"
    if "/" not in superseded_by:
        return False, f"invalid --in-favor-of id: {superseded_by!r}"

    meta_path = src / "meta.json"
    if not meta_path.exists():
        return False, f"meta.json missing at {meta_path}"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["status"] = "deprecated"
    meta["superseded_by"] = superseded_by
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    # Move to archive/<author>/<slug>
    dst = repo / "archive" / author / slug
    if dst.exists():
        return False, f"archive target already exists: {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))

    # Clean up empty author dir under skills/
    parent = repo / "skills" / author
    try:
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:
        pass

    branch = f"deprecate/{author}-{slug}"
    title = f"Deprecate {skill_id} in favor of {superseded_by}"
    body = (
        f"## Deprecation\n\n"
        f"**Skill**: `{skill_id}`\n"
        f"**Superseded by**: `{superseded_by}`\n\n"
        f"### Changes\n"
        f"- `meta.json`: `status -> \"deprecated\"`, `superseded_by -> \"{superseded_by}\"`\n"
        f"- Directory moved: `skills/{author}/{slug}/` -> `archive/{author}/{slug}/`\n"
    )

    subprocess.run(["git", "-C", str(repo), "checkout", "-B", branch], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", title], check=True, capture_output=True)

    gh = _find_gh()
    result = subprocess.run(
        [gh, "pr", "create", "--title", title, "--body", body],
        cwd=str(repo), capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False, f"gh pr create failed: {result.stderr}"
    return True, result.stdout.strip()


def run(args) -> int:
    repo = Path.cwd()
    ok, info = deprecate(repo, args.id, args.in_favor_of)
    if not ok:
        print(f"deprecate failed: {info}", file=sys.stderr)
        return 1
    print(f"Deprecation PR opened: {info}")
    return 0
