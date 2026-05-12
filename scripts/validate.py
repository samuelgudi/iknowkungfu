"""validate.py — schema + cross-file + cross-skill validation.

Usage:
  python scripts/validate.py <skill-dir>               # single skill
  python scripts/validate.py --multi <dir> [<dir>...]  # cross-skill checks
  python scripts/validate.py --all                     # all under skills/ + archive/
  python scripts/validate.py <skill-dir> --check-github-id
  python scripts/validate.py <skill-dir> --yanks <yanks.json>
  python scripts/validate.py <skill-dir> --strict
  python scripts/validate.py <skill-dir> --json

Exit codes: 0 = clean, 1 = errors found (or warnings in --strict mode).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).parent.parent
SCHEMA_FILE = Path(__file__).parent / "schema.json"

# Slug regex: ^[a-z][a-z0-9-]{0,38}[a-z0-9]$ — enforced per SCHEMA.md § 7.
SLUG_REGEX = re.compile(r"^[a-z][a-z0-9-]{0,38}[a-z0-9]$")
# Full id regex: author/slug — both components must match slug grammar.
ID_REGEX = re.compile(
    r"^[a-z][a-z0-9-]{0,38}[a-z0-9]/[a-z][a-z0-9-]{0,38}[a-z0-9]$"
)
# Semver: MAJOR.MINOR.PATCH with optional pre-release.
SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z-.]+)?$")

# Eight valid categories per SCHEMA.md § 6.
ALLOWED_CATEGORIES = {"media", "dev", "ops", "data", "comms", "docs", "meta", "ai"}

# Files that are always allowed in a skill directory root (case-sensitive).
ALLOWED_ROOT_FILES = {"SKILL.md", "meta.json", "README.md"}
# Allowed sub-directories inside a skill dir.
ALLOWED_ROOT_DIRS = {"scripts", "templates"}


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

def parse_frontmatter(skill_md: Path) -> dict:
    """Parse YAML frontmatter from SKILL.md.

    Handles Windows CRLF line endings. Raises ValueError on malformed input.
    """
    text = skill_md.read_text(encoding="utf-8")
    # Normalise Windows CRLF — git checkout on Windows may produce \r\n.
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_md}: missing YAML frontmatter delimiter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"{skill_md}: unterminated frontmatter")
    return yaml.safe_load(text[4:end]) or {}


# ---------------------------------------------------------------------------
# Per-skill validator
# ---------------------------------------------------------------------------

def validate_skill_dir(
    skill_dir: Path,
    *,
    strict: bool = False,
    check_github_id: bool = False,
    yanks_data: dict | None = None,
) -> list[dict]:
    """Validate one skill directory.

    Returns a list of issue dicts: {"severity": "error"|"warning", "msg": str}.
    """
    issues: list[dict] = []

    skill_md = skill_dir / "SKILL.md"
    meta_file = skill_dir / "meta.json"

    # --- Required files ------------------------------------------------------
    if not skill_md.is_file():
        issues.append({"severity": "error", "msg": "SKILL.md missing (must be uppercase)"})
        return issues
    if not meta_file.is_file():
        issues.append({"severity": "error", "msg": "meta.json missing"})
        return issues

    # --- Parse meta.json -----------------------------------------------------
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append({"severity": "error", "msg": f"meta.json parse error: {exc}"})
        return issues

    # --- Parse SKILL.md frontmatter ------------------------------------------
    try:
        fm = parse_frontmatter(skill_md)
    except Exception as exc:
        issues.append({"severity": "error", "msg": str(exc)})
        return issues

    # --- Required meta.json fields -------------------------------------------
    for field in ("id", "version", "status", "author", "category", "agent_compat",
                  "license", "install"):
        if field not in meta:
            issues.append({"severity": "error", "msg": f"meta.json missing required field: {field}"})

    # --- ID / slug grammar ---------------------------------------------------
    meta_id: str = meta.get("id", "")
    if meta_id and not ID_REGEX.match(meta_id):
        issues.append({
            "severity": "error",
            "msg": f"id '{meta_id}' doesn't match author/slug regex "
                   r"(^[a-z][a-z0-9-]{0,38}[a-z0-9]/[a-z][a-z0-9-]{0,38}[a-z0-9]$)",
        })

    # --- Cross-file: frontmatter name == id slug part ------------------------
    slug_part = meta_id.split("/", 1)[-1] if "/" in meta_id else meta_id
    fm_name = fm.get("name", "")
    if fm_name != slug_part:
        issues.append({
            "severity": "error",
            "msg": (
                f"frontmatter name '{fm_name}' != meta.json id slug part '{slug_part}'"
            ),
        })

    # --- Semver --------------------------------------------------------------
    version = meta.get("version", "")
    if version and not SEMVER_REGEX.match(version):
        issues.append({
            "severity": "error",
            "msg": f"version '{version}' not valid semver",
        })

    # --- Status enum ---------------------------------------------------------
    status = meta.get("status", "")
    if status and status not in ("active", "deprecated"):
        issues.append({
            "severity": "error",
            "msg": f"status '{status}' must be 'active' or 'deprecated'",
        })

    # --- Deprecation: superseded_by required ---------------------------------
    if status == "deprecated" and not meta.get("superseded_by"):
        issues.append({
            "severity": "error",
            "msg": "status=deprecated requires non-null superseded_by",
        })

    # --- Category enum -------------------------------------------------------
    category = meta.get("category")
    if category is not None and category not in ALLOWED_CATEGORIES:
        issues.append({
            "severity": "error",
            "msg": f"category '{category}' not in {sorted(ALLOWED_CATEGORIES)}",
        })

    # --- Tag cap (max 10) ----------------------------------------------------
    tags = meta.get("tags", [])
    if len(tags) > 10:
        issues.append({
            "severity": "error",
            "msg": f"tags count {len(tags)} > 10 (anti-stuffing cap)",
        })

    # --- requires sub-fields restriction -------------------------------------
    requires = meta.get("requires", {})
    if isinstance(requires, dict):
        allowed_requires = {"env_vars", "commands"}
        extra = sorted(set(requires.keys()) - allowed_requires)
        if extra:
            issues.append({
                "severity": "error",
                "msg": f"requires has unknown sub-fields: {extra}; only {sorted(allowed_requires)} allowed",
            })

    # --- Nested .git detection -----------------------------------------------
    for git_candidate in skill_dir.rglob(".git"):
        if git_candidate.is_dir():
            rel = git_candidate.relative_to(skill_dir)
            issues.append({
                "severity": "error",
                "msg": f"nested .git directory detected at {rel} inside skill tree",
            })

    # --- Extraneous files at skill root --------------------------------------
    for item in sorted(skill_dir.iterdir()):
        if item.name.startswith("."):
            # Hidden items already caught by .git check above; skip here.
            continue
        if item.is_file():
            if item.name not in ALLOWED_ROOT_FILES:
                issues.append({
                    "severity": "error",
                    "msg": f"extraneous file '{item.name}' found in skill directory root",
                })
        elif item.is_dir():
            if item.name not in ALLOWED_ROOT_DIRS:
                issues.append({
                    "severity": "error",
                    "msg": f"extraneous directory '{item.name}/' found in skill directory root",
                })

    # --- GitHub ID check (optional, requires gh CLI) -------------------------
    if check_github_id:
        author = meta.get("author", {})
        if isinstance(author, dict):
            login = author.get("github_login", "")
            declared_id = author.get("github_id")
            if login and declared_id is not None:
                import shutil as _shutil
                # Use shutil.which so .bat shims on Windows are resolved
                # before system gh.exe, respecting PATH + PATHEXT ordering.
                gh_exe = _shutil.which("gh") or "gh"
                try:
                    proc = subprocess.run(
                        [gh_exe, "api", f"users/{login}"],
                        capture_output=True, text=True, timeout=15,
                    )
                    if proc.returncode == 0:
                        gh_data = json.loads(proc.stdout)
                        actual_id = gh_data.get("id")
                        if actual_id != declared_id:
                            issues.append({
                                "severity": "error",
                                "msg": (
                                    f"author.github_id {declared_id} does not match "
                                    f"GitHub API response for '{login}' (actual: {actual_id})"
                                ),
                            })
                    else:
                        issues.append({
                            "severity": "warning",
                            "msg": f"github_id check skipped: gh CLI returned non-zero for '{login}'",
                        })
                except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as exc:
                    issues.append({
                        "severity": "warning",
                        "msg": f"github_id check skipped (network/CLI unavailable): {exc}",
                    })

    # --- Yank reason validation (when yanks data is provided) ----------------
    if yanks_data is not None:
        skill_id = meta.get("id", "")
        for entry in yanks_data.get("yanks", []):
            if entry.get("id") == skill_id:
                reason = entry.get("reason", "")
                if not isinstance(reason, str) or not reason.strip():
                    issues.append({
                        "severity": "error",
                        "msg": (
                            f"yanks.json entry for '{skill_id}' v{entry.get('version', '?')} "
                            f"has empty or missing reason field"
                        ),
                    })

    return issues


# ---------------------------------------------------------------------------
# Cross-skill validator
# ---------------------------------------------------------------------------

def _detect_cycle(graph: dict[str, list[str]], label: str) -> list[dict]:
    """Detect cycles in a graph (adjacency list: id -> [id, ...]).

    Returns a list of error issues for each cycle found.
    """
    issues: list[dict] = []
    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node: str, path: list[str]) -> None:
        if node in in_stack:
            cycle_start = path.index(node)
            cycle = " -> ".join(path[cycle_start:] + [node])
            issues.append({
                "severity": "error",
                "msg": f"{label} cycle detected: {cycle}",
            })
            return
        if node in visited:
            return
        visited.add(node)
        in_stack.add(node)
        for neighbour in graph.get(node, []):
            dfs(neighbour, path + [node])
        in_stack.discard(node)

    for node in sorted(graph):
        if node not in visited:
            dfs(node, [])
    return issues


def validate_skill_set(
    skill_dirs: list[Path],
    *,
    strict: bool = False,
) -> list[dict]:
    """Cross-skill validation: cycles, collisions, dangling superseded_by refs.

    Runs AFTER per-skill validation. Returns a flat list of issues (no path key).
    """
    issues: list[dict] = []

    # Collect all metas (skip dirs that failed per-skill parse)
    id_to_meta: dict[str, dict] = {}
    for d in skill_dirs:
        meta_file = d / "meta.json"
        if not meta_file.is_file():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        skill_id = meta.get("id", "")
        if skill_id:
            id_to_meta[skill_id] = meta

    all_ids = set(id_to_meta)

    # --- Slug collision: two different authors share the same slug -----------
    slug_to_authors: dict[str, list[str]] = {}
    for skill_id in sorted(all_ids):
        parts = skill_id.split("/", 1)
        if len(parts) == 2:
            author, slug = parts
            slug_to_authors.setdefault(slug, []).append(author)
    for slug, authors in sorted(slug_to_authors.items()):
        if len(authors) > 1:
            issues.append({
                "severity": "error",
                "msg": (
                    f"slug collision: slug '{slug}' is registered by multiple authors: "
                    f"{sorted(authors)}"
                ),
            })

    # --- superseded_by references must point to existing skill IDs ----------
    for skill_id, meta in sorted(id_to_meta.items()):
        successor = meta.get("superseded_by")
        if successor and successor not in all_ids:
            issues.append({
                "severity": "error",
                "msg": (
                    f"'{skill_id}' superseded_by '{successor}' refers to unknown skill"
                ),
            })

    # --- Deprecation cycle (superseded_by graph) ----------------------------
    dep_graph: dict[str, list[str]] = {}
    for skill_id, meta in id_to_meta.items():
        successor = meta.get("superseded_by")
        if successor:
            dep_graph[skill_id] = [successor]
    issues.extend(_detect_cycle(dep_graph, "superseded_by"))

    # --- Composes cycle -----------------------------------------------------
    composes_graph: dict[str, list[str]] = {}
    for skill_id, meta in id_to_meta.items():
        composes = meta.get("composes", [])
        if composes:
            composes_graph[skill_id] = list(composes)
    issues.extend(_detect_cycle(composes_graph, "composes"))

    # --- Extends cycle ------------------------------------------------------
    extends_graph: dict[str, list[str]] = {}
    for skill_id, meta in id_to_meta.items():
        extends = meta.get("extends")
        if extends:
            extends_graph[skill_id] = [extends]
    issues.extend(_detect_cycle(extends_graph, "extends"))

    return issues


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Validate iknowkungfu skill directories."
    )
    p.add_argument("target", nargs="?", help="Single skill directory to validate.")
    p.add_argument("--all", action="store_true",
                   help="Validate all skills under skills/ and archive/.")
    p.add_argument("--multi", action="store_true",
                   help="Cross-skill mode: validate multiple dirs with cross-skill checks.")
    p.add_argument("--strict", action="store_true",
                   help="Treat warnings as errors.")
    p.add_argument("--json", action="store_true",
                   help="Output results as JSON.")
    p.add_argument("--check-github-id", action="store_true",
                   help="Verify author.github_id against the GitHub API (requires gh CLI).")
    p.add_argument("--yanks", metavar="FILE",
                   help="Path to yanks.json to check yank reason fields.")
    p.add_argument("dirs", nargs="*",
                   help="Skill directories (used with --multi).")
    args = p.parse_args(argv)

    # Load yanks data if provided
    yanks_data: dict | None = None
    if args.yanks:
        yanks_path = Path(args.yanks)
        try:
            yanks_data = json.loads(yanks_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"ERROR  cannot load yanks file: {exc}", file=sys.stderr)
            return 1

    # Collect targets
    targets: list[Path] = []
    if args.multi:
        # argparse quirk: with nargs="?" on target, the first positional after
        # --multi is consumed as target; rest go to dirs. Collect both.
        raw: list[str] = []
        if args.target:
            raw.append(args.target)
        raw.extend(args.dirs)
        targets = [Path(d) for d in raw]
        if not targets:
            p.error("--multi requires at least one directory argument")
    elif args.all:
        for parent in (ROOT / "skills", ROOT / "archive"):
            if parent.exists():
                for author in sorted(parent.iterdir()):
                    if author.is_dir():
                        for slug_dir in sorted(author.iterdir()):
                            if slug_dir.is_dir():
                                targets.append(slug_dir)
    elif args.target:
        targets.append(Path(args.target))
    else:
        p.error("target or --all or --multi required")

    # Per-skill validation
    all_issues: dict[str, list[dict]] = {}
    for t in targets:
        all_issues[str(t)] = validate_skill_dir(
            t,
            strict=args.strict,
            check_github_id=args.check_github_id,
            yanks_data=yanks_data,
        )

    # Cross-skill validation (only when multiple dirs provided)
    cross_issues: list[dict] = []
    if len(targets) > 1 or args.multi or args.all:
        cross_issues = validate_skill_set(targets, strict=args.strict)

    # Output
    if args.json:
        result = {
            "per_skill": all_issues,
            "cross_skill": cross_issues,
        }
        print(json.dumps(result, indent=2))
    else:
        for path, issues in all_issues.items():
            if not issues:
                print(f"{path}: clean")
                continue
            print(f"{path}:")
            for i in issues:
                print(f"  {i['severity'].upper()}  {i['msg']}")
        if cross_issues:
            print("cross-skill:")
            for i in cross_issues:
                print(f"  {i['severity'].upper()}  {i['msg']}")

    has_errors = any(
        i["severity"] == "error"
        for issues in all_issues.values()
        for i in issues
    ) or any(i["severity"] == "error" for i in cross_issues)

    has_warnings = any(
        i["severity"] == "warning"
        for issues in all_issues.values()
        for i in issues
    ) or any(i["severity"] == "warning" for i in cross_issues)

    if has_errors:
        return 1
    if has_warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
