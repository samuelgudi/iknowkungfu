"""generate_manifest.py — build registry.json from skills/ + yanks.json + git log."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _to_utc_z(iso_str: str) -> str:
    """Normalize an ISO 8601 timestamp to UTC with `Z` suffix. Without this,
    `git log --format=%cI` emits the local timezone of wherever the script runs
    (Ubuntu/UTC in GHA, CEST on a Windows dev box), producing non-deterministic
    manifests across platforms — which in turn breaks the rollback guard's
    naive-string comparison and any byte-equal diff check."""
    s = (iso_str or "").strip()
    if not s:
        return ""
    # datetime.fromisoformat in Python 3.10 doesn't accept 'Z'.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return iso_str  # Pass through unrecognised values rather than dropping data.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Ensure repo root is on sys.path so `adapters._base` is importable when this
# script is invoked directly (e.g. `python scripts/generate_manifest.py`) from
# a non-editable-installed checkout. In CI, `pip install -e .[dev]` makes the
# package importable without this shim; the shim is a no-op in that case.
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from adapters._base import compute_dir_content_hash


ROOT = Path(__file__).parent.parent


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    # Handle Windows CRLF
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end])



def _posix(p) -> str:
    """Normalise a Path or path string to forward-slash form.
    Required because `git show <sha>:<path>` and `git log -- <path>` reject
    backslash paths on Windows (the file isn't found in the index)."""
    return str(p).replace("\\", "/")


def get_git_tree_sha(repo: Path, skill_path: Path) -> str:
    rel = skill_path.relative_to(repo)
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%T", "--", _posix(rel)],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def get_skill_versions(repo: Path, skill_dir: Path) -> dict:
    """Walk git log for the skill's meta.json; record each version's tree SHA + release date."""
    meta_rel = _posix((skill_dir / "meta.json").relative_to(repo))
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse", "--format=%H %cI", "--", meta_rel],
        capture_output=True, text=True
    )
    versions = {}
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        commit_sha, released = line.split(maxsplit=1)
        show = subprocess.run(
            ["git", "-C", str(repo), "show", f"{commit_sha}:{meta_rel}"],
            capture_output=True, text=True, encoding="utf-8"
        )
        try:
            meta = json.loads(show.stdout)
        except json.JSONDecodeError:
            continue
        ver = meta.get("version")
        if not ver or ver in versions:
            continue
        tree_sha_result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{commit_sha}^{{tree}}"],
            capture_output=True, text=True
        )
        versions[ver] = {
            "sha": tree_sha_result.stdout.strip(),
            "released": _to_utc_z(released),
        }
    return versions


def get_commit_timestamp(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%cI", "HEAD"],
        capture_output=True, text=True
    )
    return _to_utc_z(result.stdout.strip()) or "1970-01-01T00:00:00Z"


def get_provenance(repo: Path, skill_dir: Path) -> dict:
    rel = _posix(skill_dir.relative_to(repo))
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%cI %s", "--", rel],
        capture_output=True, text=True
    )
    line = result.stdout.strip()
    if not line:
        return {}
    merged_at, msg = line.split(maxsplit=1)
    pr_match = None
    m = re.search(r"#(\d+)", msg)
    if m:
        pr_match = int(m.group(1))
    prov: dict = {"merged_at": _to_utc_z(merged_at), "reviewed_by": "samuelgudi"}
    if pr_match is not None:
        prov["submitted_pr"] = pr_match
    return prov


def build_skill_entry(repo: Path, skill_dir: Path, status: str) -> dict:
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    fm = parse_frontmatter(skill_dir / "SKILL.md")
    content_hash = compute_dir_content_hash(skill_dir)
    files = sorted(
        str(f.relative_to(skill_dir)).replace("\\", "/")
        for f in skill_dir.rglob("*") if f.is_file()
    )
    has_scripts = (skill_dir / "scripts").is_dir()
    # Derive skill id from directory path: <author_dir>/<slug_dir>.
    # Enforce the slug grammar here too (same regex as validate.py) — the id
    # flows into every client's install-path computation, so a malformed
    # directory name must never be baked into registry.json.
    author_name = skill_dir.parent.name
    slug_name = skill_dir.name
    slug_re = re.compile(r"^[a-z][a-z0-9-]{0,38}[a-z0-9]$")
    if not slug_re.match(author_name) or not slug_re.match(slug_name):
        raise SystemExit(
            f"ERROR: directory {skill_dir} does not match the <author>/<slug> "
            f"grammar (^[a-z][a-z0-9-]{{0,38}}[a-z0-9]$ per component); refusing to manifest it"
        )
    skill_id = f"{author_name}/{slug_name}"
    versions = get_skill_versions(repo, skill_dir) or {
        meta["version"]: {
            "sha": get_git_tree_sha(repo, skill_dir),
            "released": get_commit_timestamp(repo),
        }
    }
    entry = {
        "id": skill_id,
        "name": fm.get("name", slug_name),
        "description": fm.get("description", ""),
        "version": meta["version"],
        "status": status,
        "author": meta["author"],
        "category": meta["category"],
        "tags": meta.get("tags", []),
        "platforms": meta.get("platforms", ["linux", "macos", "windows"]),
        "agent_compat": meta["agent_compat"],
        "requires": meta.get("requires", {"env_vars": [], "commands": []}),
        "has_scripts": has_scripts,
        "license": meta["license"],
        "install": meta["install"],
        "source": {
            "path": str(skill_dir.relative_to(repo)).replace("\\", "/"),
            "content_hash": content_hash,
            "files": files,
        },
        "versions": versions,
        "provenance": get_provenance(repo, skill_dir),
        "composes": meta.get("composes", []),
        "extends": meta.get("extends"),
        "supersedes": meta.get("supersedes", []),
        "superseded_by": meta.get("superseded_by"),
    }
    # `origin` (ADR-002) is author-supplied and present only on imported
    # skills. Include it only when present so first-party entries stay clean.
    if meta.get("origin"):
        entry["origin"] = meta["origin"]
    return entry


def load_yanks(repo: Path) -> dict:
    yanks_path = repo / "yanks.json"
    if not yanks_path.exists():
        return {}
    data = json.loads(yanks_path.read_text(encoding="utf-8"))
    out = {}
    for y in data.get("yanks", []):
        out.setdefault(y["id"], {})[y["version"]] = {"yanked": True, "yank_reason": y["reason"]}
    return out


def apply_yanks(skills: list[dict], yanks: dict) -> None:
    for s in skills:
        for ver, info in yanks.get(s["id"], {}).items():
            if ver in s["versions"]:
                s["versions"][ver].update(info)


def build_manifest(repo: Path) -> dict:
    skills = []
    for status, parent in [("active", repo / "skills"), ("deprecated", repo / "archive")]:
        if not parent.exists():
            continue
        for author in sorted(parent.iterdir()):
            if not author.is_dir():
                continue
            for slug in sorted(author.iterdir()):
                if slug.is_dir() and (slug / "meta.json").exists():
                    skills.append(build_skill_entry(repo, slug, status))
    skills.sort(key=lambda s: s["id"])
    apply_yanks(skills, load_yanks(repo))
    return {
        "schema_version": 2,
        "generated_at": get_commit_timestamp(repo),
        "skills": skills,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args(argv)

    repo = Path.cwd()
    manifest = build_manifest(repo)
    serialized = json.dumps(manifest, indent=2, sort_keys=False) + "\n"

    reg_path = repo / "registry.json"
    if args.check:
        if not reg_path.exists():
            print("registry.json missing.")
            return 1
        try:
            current = json.loads(reg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"registry.json parse error: {e}")
            return 1
        # Compare structural content (skills array + schema_version), ignoring
        # generated_at which reflects HEAD's commit time and necessarily drifts
        # on every commit. The on-merge workflow refreshes generated_at; --check
        # only flags semantic drift in the skills array.
        current_skills = current.get("skills")
        manifest_skills = manifest["skills"]
        if current.get("schema_version") != manifest["schema_version"] or current_skills != manifest_skills:
            print("registry.json out of sync. Run generate_manifest.py to regenerate.", file=sys.stderr)
            return 1
        return 0
    reg_path.write_text(serialized, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
