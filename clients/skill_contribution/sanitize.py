"""Interactive sanitization of skill contributions."""
from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from clients.skill_contribution.sanitize_rules import RULES


# File extensions considered "text" — others are copied unchanged.
TEXT_EXTS = {".md", ".py", ".js", ".ts", ".sh", ".bash", ".zsh", ".json", ".yaml", ".yml", ".txt", ".toml"}


@dataclass
class Detection:
    file: Path           # source path
    rel: str             # path relative to src_dir
    line: int
    col: int
    match: str
    rule_id: str
    placeholder: str
    description: str


@dataclass
class SanitizeResult:
    accepted: list[Detection] = field(default_factory=list)
    skipped: list[Detection] = field(default_factory=list)
    cancelled: bool = False


def _is_text_file(p: Path) -> bool:
    return p.suffix.lower() in TEXT_EXTS or p.name in {"SKILL.md", "skill.md", "README.md"}


def _compile_rules(scope: str) -> list[tuple[dict, re.Pattern]]:
    """Return list of (rule, compiled_pattern) for the given scope.
    scope: 'skill_md' or 'other'."""
    out = []
    for rule in RULES:
        skill_md_only = rule.get("skill_md_only", False)
        if scope == "skill_md" or not skill_md_only:
            out.append((rule, re.compile(rule["pattern"])))
    return out


def scan(src_dir: Path) -> list[Detection]:
    """Walk src_dir, scan every text file. Return list of Detection sorted by (file, line, col)."""
    detections: list[Detection] = []
    skill_md_rules = _compile_rules("skill_md")
    other_rules = _compile_rules("other")
    for path in sorted(src_dir.rglob("*")):
        if not path.is_file() or not _is_text_file(path):
            continue
        rel = str(path.relative_to(src_dir)).replace("\\", "/")
        is_skill_md = path.name.lower() == "skill.md"
        rules_for_file = skill_md_rules if is_skill_md else other_rules
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for rule, regex in rules_for_file:
            for m in regex.finditer(text):
                line = text[: m.start()].count("\n") + 1
                last_nl = text.rfind("\n", 0, m.start())
                col = m.start() - (last_nl + 1) + 1
                detections.append(Detection(
                    file=path, rel=rel, line=line, col=col,
                    match=m.group(0), rule_id=rule["id"],
                    placeholder=rule["placeholder"], description=rule["description"],
                ))
    detections.sort(key=lambda d: (d.rel, d.line, d.col))
    return detections


def _prompt(detection: Detection, *, yes: bool, prompt_fn=input) -> str:
    """Return 'a' (accept), 's' (skip), or 'c' (cancel)."""
    if yes:
        return "a"
    print()
    print(f"  {detection.rel}:{detection.line}:{detection.col}  [{detection.rule_id}]  {detection.description}")
    print(f"    Found:       {detection.match}")
    print(f"    Replacement: {detection.placeholder}")
    while True:
        choice = prompt_fn("    [a]ccept / [s]kip / [c]ancel: ").strip().lower()
        if choice in ("a", "s", "c"):
            return choice
        print("    Please answer a, s, or c.")


def apply(src_dir: Path, dst_dir: Path, accepted: list[Detection]) -> None:
    """Copy src_dir -> dst_dir, applying replacements grouped by file.
    All occurrences of the same secret string are replaced (intentional).
    """
    if dst_dir.exists():
        raise FileExistsError(f"{dst_dir} already exists")
    shutil.copytree(src_dir, dst_dir)
    # Group accepted detections by relative path
    by_rel: dict[str, list[Detection]] = {}
    for d in accepted:
        by_rel.setdefault(d.rel, []).append(d)
    for rel, dets in by_rel.items():
        target = dst_dir / rel
        text = target.read_text(encoding="utf-8", errors="replace")
        # Replace all occurrences of each unique match string.
        # If the same secret appears multiple times, all occurrences are replaced.
        unique = {d.match: d.placeholder for d in dets}
        for needle, repl in unique.items():
            text = text.replace(needle, repl)
        target.write_text(text, encoding="utf-8")


def sanitize(src_dir: Path, dst_dir: Path, *, yes: bool = False, prompt_fn=input) -> SanitizeResult:
    """Top-level entry: scan, prompt, apply."""
    detections = scan(src_dir)
    result = SanitizeResult()
    if not detections:
        # Even with zero detections, produce a sanitized copy at dst_dir.
        if dst_dir.exists():
            raise FileExistsError(f"{dst_dir} already exists")
        shutil.copytree(src_dir, dst_dir)
        return result

    print(f"Sanitizing {src_dir} -> {dst_dir}")
    print(f"  {len(detections)} potential issue(s) found.")
    for d in detections:
        choice = _prompt(d, yes=yes, prompt_fn=prompt_fn)
        if choice == "a":
            result.accepted.append(d)
        elif choice == "s":
            result.skipped.append(d)
        else:  # 'c'
            result.cancelled = True
            return result
    apply(src_dir, dst_dir, result.accepted)
    print()
    print(f"  Accepted: {len(result.accepted)}; Skipped: {len(result.skipped)}")
    return result
