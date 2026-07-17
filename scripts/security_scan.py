"""security_scan.py — pattern-based scan of scripts/ and templates/."""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).parent.parent
RULES_FILE = Path(__file__).parent / "rules.yaml"

LANG_BY_EXT = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".ts": "javascript", ".mjs": "javascript",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".md": "markdown",
}


def load_rules() -> list[dict]:
    with open(RULES_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rules = data["rules"]
    for r in rules:
        r["_compiled"] = re.compile(r["pattern"], re.MULTILINE)
    return rules


def file_language(path: Path) -> str:
    return LANG_BY_EXT.get(path.suffix.lower(), "unknown")


def rule_applies(rule: dict, path: Path, lang: str, repo_relpath: str) -> bool:
    languages = rule.get("languages")
    if languages and lang not in languages:
        return False
    scope = rule.get("scope")
    if scope and not fnmatch.fnmatch(repo_relpath, scope):
        return False
    return True


def scan_file(path: Path, rules: list[dict], repo_relpath: str) -> list[dict]:
    findings = []
    lang = file_language(path)
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings
    for rule in rules:
        if not rule_applies(rule, path, lang, repo_relpath):
            continue
        for match in rule["_compiled"].finditer(content):
            line = content[: match.start()].count("\n") + 1
            findings.append({
                "file": str(path),
                "line": line,
                "rule_id": rule["id"],
                "severity": rule["severity"],
                "message": rule["message"],
                "fix_hint": rule.get("fix_hint", ""),
            })
    return findings


def scan_skill_dir(skill_dir: Path, rules: list[dict]) -> list[dict]:
    findings = []
    # Determine the base for repo-relative path computation.
    # For skills inside the repo tree, use ROOT so that scope patterns like
    # "adapters/**" resolve correctly.  For skills outside (e.g. tmp_path in
    # tests), fall back to skill_dir.parent so that scope patterns like
    # "scripts/**" still fire when a file sits at <skill_dir>/scripts/<file>.
    try:
        skill_dir.relative_to(ROOT)
        relbase = ROOT
    except ValueError:
        # skill_dir is outside the repo (e.g. tmp_path in tests).
        # Use skill_dir itself as the base so that a file at
        # <skill_dir>/scripts/foo.py gets relpath "scripts/foo.py",
        # which correctly matches scope patterns like "scripts/**".
        relbase = skill_dir

    for sub in ("scripts", "templates"):
        target = skill_dir / sub
        if not target.exists():
            continue
        for f in target.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(relbase)).replace("\\", "/")
                findings.extend(scan_file(f, rules, rel))

    # Markdown is the primary attack surface of an instructions registry:
    # SKILL.md (and any references/*.md) is loaded verbatim into an agent's
    # context, so it gets pattern-scanned too.
    for f in skill_dir.rglob("*.md"):
        if not f.is_file():
            continue
        parts = f.relative_to(skill_dir).parts
        if parts and parts[0] in ("scripts", "templates"):
            continue  # already scanned above
        rel = str(f.relative_to(relbase)).replace("\\", "/")
        findings.extend(scan_file(f, rules, rel))
    return findings


def main(argv: list[str] | None = None) -> int:
    # Rule messages are UTF-8; Windows consoles default to a legacy codepage.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("target", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    rules = load_rules()
    targets: list[Path] = []
    if args.all:
        for parent in (ROOT / "skills", ROOT / "archive"):
            if parent.exists():
                for author in parent.iterdir():
                    for slug in author.iterdir():
                        if slug.is_dir():
                            targets.append(slug)
    elif args.target:
        targets.append(Path(args.target))
    else:
        p.error("target or --all required")

    all_findings = []
    for t in targets:
        all_findings.extend(scan_skill_dir(t, rules))

    if args.json:
        print(json.dumps(all_findings, indent=2))
    else:
        if not all_findings:
            print("clean")
        else:
            for f in all_findings:
                print(f"  {f['file']}")
                print(f"    line {f['line']}  {f['severity'].upper()}  {f['rule_id']}  {f['message']}")
                if f.get("fix_hint"):
                    print(f"                fix: {f['fix_hint']}")

    blocks = [f for f in all_findings if f["severity"] == "block"]
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
