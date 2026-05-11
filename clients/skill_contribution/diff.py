"""Generate SANITIZATION.diff: unified diff of pre- vs post-sanitization."""
from __future__ import annotations

import difflib
from pathlib import Path


def _read_lines(p: Path) -> list[str]:
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except (OSError, UnicodeDecodeError):
        return []


def _relative_files(root: Path) -> set[str]:
    return {
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file()
    }


def generate_diff(pre: Path, post: Path) -> str:
    """Return a unified diff string of files in pre vs post. Only files that changed are included.
    Files present in only one side are shown as full-add or full-remove."""
    pre_files = _relative_files(pre)
    post_files = _relative_files(post)
    all_files = sorted(pre_files | post_files)

    parts: list[str] = []
    for rel in all_files:
        pre_path = pre / rel
        post_path = post / rel
        pre_lines = _read_lines(pre_path) if rel in pre_files else []
        post_lines = _read_lines(post_path) if rel in post_files else []
        if pre_lines == post_lines:
            continue
        diff = difflib.unified_diff(
            pre_lines,
            post_lines,
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm="",
        )
        parts.extend(diff)
        parts.append("")  # blank line between file sections
    return "\n".join(parts)


def write_diff(pre: Path, post: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(generate_diff(pre, post), encoding="utf-8")
