"""yank verb — hard compromise: append to yanks.json + open PR. Per Decision #10 (Gemini M3)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_gh() -> str:
    import shutil
    found = shutil.which("gh")
    if found:
        return found
    raise SystemExit("gh CLI not found on PATH.")


def _parse_spec(spec: str) -> tuple[str | None, str | None]:
    if "@" not in spec:
        return spec, None
    skill_id, version = spec.split("@", 1)
    return skill_id, version


def _find_skill(registry: dict, skill_id: str) -> dict | None:
    for s in registry.get("skills", []):
        if s["id"] == skill_id:
            return s
    return None


def _detect_yanker(repo: Path) -> str:
    """Get the GitHub login of the person opening the yank. Falls back to 'unknown'."""
    import shutil
    gh = shutil.which("gh")
    if not gh:
        return "unknown"
    try:
        r = subprocess.run([gh, "api", "user"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return json.loads(r.stdout).get("login", "unknown")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        pass
    return "unknown"


def yank(repo: Path, spec: str, reason: str) -> tuple[bool, str | None]:
    """Apply the yank locally and open a PR. Returns (success, pr_url_or_error)."""
    repo = Path(repo).resolve()

    skill_id, version = _parse_spec(spec)
    if not skill_id or not version:
        return False, f"invalid spec {spec!r}; expected <id>@<version>"
    if "/" not in skill_id:
        return False, f"invalid skill id {skill_id!r}; expected <author>/<slug>"
    if not reason or not reason.strip():
        return False, "reason must be non-empty"

    # Load registry.json + verify version exists
    reg_path = repo / "registry.json"
    if not reg_path.exists():
        return False, f"registry.json not found at {reg_path}"
    try:
        registry = json.loads(reg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"registry.json parse error: {e}"

    skill = _find_skill(registry, skill_id)
    if skill is None:
        return False, f"skill {skill_id} not found in registry.json"
    versions = skill.get("versions", {})
    if version not in versions:
        available = ", ".join(sorted(versions.keys())) or "(none)"
        return False, f"version {version} not found for {skill_id}. Available: {available}"

    # Check the version isn't already yanked
    if versions[version].get("yanked", False):
        return False, f"{skill_id}@{version} is already yanked"

    # Load yanks.json (sibling to registry.json)
    yanks_path = repo / "yanks.json"
    if yanks_path.exists():
        try:
            yanks_data = json.loads(yanks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            yanks_data = {"yanks": []}
    else:
        yanks_data = {"yanks": []}

    # Refuse duplicate entry (check both yanks.json content and existing branch)
    for existing in yanks_data.get("yanks", []):
        if existing.get("id") == skill_id and existing.get("version") == version:
            return False, f"{skill_id}@{version} already in yanks.json"

    # Also refuse if the yank branch already exists (covers the case where main was checked out
    # after the first yank but the PR branch is still present)
    author_check, slug_check = skill_id.split("/", 1)
    branch_check = f"yank/{author_check}-{slug_check}-{version}"
    r_branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--list", branch_check],
        capture_output=True, text=True,
    )
    if r_branch.returncode == 0 and branch_check in r_branch.stdout:
        return False, f"{skill_id}@{version} already in yanks.json (branch {branch_check} exists)"

    yanker = _detect_yanker(repo)
    entry = {
        "id": skill_id,
        "version": version,
        "reason": reason.strip(),
        "yanked_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "yanked_by": yanker,
    }
    yanks_data.setdefault("yanks", []).append(entry)
    yanks_path.write_text(json.dumps(yanks_data, indent=2) + "\n", encoding="utf-8")

    # Branch + commit + PR
    author, slug = skill_id.split("/", 1)
    branch = f"yank/{author}-{slug}-{version}"
    title = f"Yank {skill_id}@{version}"
    body = (
        f"## Yank\n\n"
        f"**Skill**: `{skill_id}`\n"
        f"**Version**: `{version}`\n"
        f"**Reason**: {reason}\n"
        f"**Yanked by**: `{yanker}`\n\n"
        f"### Effect\n"
        f"After merge, `generate_manifest.py` will set `versions[\"{version}\"].yanked = true` "
        f"in `registry.json`. All clients will hard-refuse to install this version on next "
        f"`agent-skills update`. There is no override flag.\n"
    )

    subprocess.run(["git", "-C", str(repo), "checkout", "-B", branch], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "yanks.json"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", title], check=True, capture_output=True)

    gh = _find_gh()
    r = subprocess.run(
        [gh, "pr", "create", "--title", title, "--body", body],
        cwd=str(repo), capture_output=True, text=True,
    )
    if r.returncode != 0:
        return False, f"gh pr create failed: {r.stderr}"
    return True, r.stdout.strip()


def run(args) -> int:
    repo = Path.cwd()
    ok, info = yank(repo, args.spec, args.reason)
    if not ok:
        print(f"yank failed: {info}", file=sys.stderr)
        return 1
    print(f"Yank PR opened: {info}")
    return 0
