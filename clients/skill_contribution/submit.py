"""5-step contribution pipeline: validate → sanitize → security_scan → REVIEW.md → git + PR."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


def _find_gh() -> str:
    """Resolve the `gh` executable, respecting PATH order (important on Windows where
    shutil.which honours PATHEXT priority correctly, unlike CreateProcess which prefers .exe)."""
    found = shutil.which("gh")
    if found:
        return found
    return "gh"  # fallback: let subprocess raise FileNotFoundError

from clients.skill_contribution import diff as diff_mod
from clients.skill_contribution import sanitize as sanitize_mod


TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class SubmitResult:
    success: bool
    pr_url: str | None = None
    error: str | None = None


def _abs(p) -> Path:
    return Path(p).resolve()


def _ensure_skill_md(skill_dir: Path) -> Path | None:
    """Detect SKILL.md vs skill.md per Decision #16. Rename lowercase. Return canonical path or None."""
    names = set(os.listdir(skill_dir))
    has_upper = "SKILL.md" in names
    has_lower = "skill.md" in names
    if has_upper and has_lower:
        return None  # ambiguous
    if has_lower and not has_upper:
        old = skill_dir / "skill.md"
        new = skill_dir / "SKILL.md"
        # On Windows (case-insensitive FS), a direct rename of skill.md -> SKILL.md is a no-op.
        # Use a two-step rename via a temporary name to force the case change.
        tmp = skill_dir / "_SKILL_TMP_.md"
        old.rename(tmp)
        tmp.rename(new)
        print(f"  Renamed skill.md -> SKILL.md", file=sys.stderr)
        return new
    if has_upper:
        return skill_dir / "SKILL.md"
    return None


def _render_review(meta: dict, dst: Path) -> None:
    tpl = (TEMPLATES_DIR / "review.md").read_text(encoding="utf-8")
    has_scripts = bool(meta.get("requires", {}).get("commands"))
    test_evidence = (
        "<paste commands run + actual outputs — REQUIRED for has_scripts skills>"
        if has_scripts
        else "(instructions-only skill — test evidence may be omitted)"
    )
    rendered = tpl.format(
        skill_id=meta["id"],
        version=meta["version"],
        description=meta.get("description", "<one-line>"),
        env_vars=", ".join(meta.get("requires", {}).get("env_vars", []) or ["none"]),
        commands=", ".join(meta.get("requires", {}).get("commands", []) or ["none"]),
        test_evidence_section=test_evidence,
    )
    dst.write_text(rendered, encoding="utf-8")


def _render_pr_body(meta: dict, slug_path: str, san_acc: int, san_skip: int,
                    scan_findings: list[dict], files: list[str]) -> str:
    tpl = (TEMPLATES_DIR / "pr-body.md").read_text(encoding="utf-8")
    return tpl.format(
        skill_id=meta["id"],
        version=meta["version"],
        category=meta.get("category", "?"),
        license=meta.get("license", "?"),
        author_login=meta["author"]["github_login"],
        author_id=meta["author"]["github_id"],
        agents=", ".join(meta.get("agent_compat", [])),
        files_list="\n".join(f"- {f}" for f in files),
        san_accepted=san_acc,
        san_skipped=san_skip,
        scan_blocks=sum(1 for f in scan_findings if f.get("severity") == "block"),
        scan_warns=sum(1 for f in scan_findings if f.get("severity") == "warn"),
        slug_path=slug_path,
    )


def submit_skill(target: Path, repo: Path, *, yes: bool = False) -> SubmitResult:
    target = _abs(target)
    repo = _abs(repo)

    # Step 0
    skill_md = _ensure_skill_md(target)
    if skill_md is None:
        return SubmitResult(False, error="SKILL.md missing or ambiguous (both upper- and lowercase variants present).")
    if not (target / "meta.json").exists():
        return SubmitResult(False, error="meta.json missing — run `kfu init <target>` first.")
    meta = json.loads((target / "meta.json").read_text(encoding="utf-8"))
    author = meta["author"]["github_login"]
    slug = meta["id"].split("/", 1)[1]
    flat = f"{author}-{slug}"
    slug_path = flat

    # Step 1 — validate
    val = subprocess.run(
        [sys.executable, str(repo / "scripts/validate.py"), str(target)],
        capture_output=True, text=True,
    )
    if val.returncode != 0:
        return SubmitResult(False, error=f"validate.py failed: {val.stdout}{val.stderr}")

    # Step 2 — sanitize
    submitted_root = repo / "submitted" / flat
    if submitted_root.exists():
        shutil.rmtree(submitted_root)
    sanitized_dir = submitted_root / author / slug
    san_result = sanitize_mod.sanitize(target, sanitized_dir, yes=yes)
    if san_result.cancelled:
        if submitted_root.exists():
            shutil.rmtree(submitted_root)
        return SubmitResult(False, error="sanitization cancelled by user")

    # Step 3 — security_scan
    scan = subprocess.run(
        [sys.executable, str(repo / "scripts/security_scan.py"), str(sanitized_dir), "--json"],
        capture_output=True, text=True,
    )
    findings = json.loads(scan.stdout) if scan.stdout.strip().startswith("[") else []
    (submitted_root / "scan_results.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    if any(f.get("severity") == "block" for f in findings):
        return SubmitResult(False, error=f"security_scan.py found hard-blocks: see {submitted_root / 'scan_results.json'}")

    # Step 4 — REVIEW.md
    _render_review(meta, submitted_root / "REVIEW.md")

    # Step 5 — SANITIZATION.diff
    diff_mod.write_diff(target, sanitized_dir, submitted_root / "SANITIZATION.diff")

    # Step 6 — git + gh
    branch = f"contrib/{flat}"
    files_list = [
        str(p.relative_to(sanitized_dir)).replace("\\", "/")
        for p in sanitized_dir.rglob("*") if p.is_file()
    ]
    pr_body = _render_pr_body(
        meta, slug_path,
        len(san_result.accepted), len(san_result.skipped),
        findings, files_list,
    )
    title = f"Submit {meta['id']} v{meta['version']}"

    # Switch to a fresh branch (delete if exists)
    subprocess.run(["git", "-C", str(repo), "checkout", "-B", branch], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", f"submitted/{flat}"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", title], check=True, capture_output=True)

    # Push the branch to origin. Without this, `gh pr create` aborts with
    # "you must first push the current branch to a remote" in non-interactive mode.
    # --force-with-lease is safe on a fresh branch (no remote ref to lease against) and
    # tolerates re-submission cycles where the local contrib branch was rebuilt.
    push = subprocess.run(
        ["git", "-C", str(repo), "push", "-u", "--force-with-lease", "origin", branch],
        capture_output=True, text=True,
    )
    if push.returncode != 0:
        return SubmitResult(False, error=f"git push failed: {push.stderr.strip() or push.stdout.strip()}")

    gh_exe = _find_gh()
    gh = subprocess.run(
        [gh_exe, "pr", "create", "--title", title, "--body", pr_body],
        cwd=str(repo), capture_output=True, text=True,
    )
    if gh.returncode != 0:
        return SubmitResult(False, error=f"gh pr create failed: {gh.stderr}")
    pr_url = gh.stdout.strip()
    return SubmitResult(True, pr_url=pr_url)
