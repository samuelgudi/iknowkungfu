"""generate_manifest.py — build registry.json from skills/ + yanks.json + git log."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


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


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def compute_content_hash(skill_dir: Path) -> tuple[str, list[str]]:
    files = sorted(
        f.relative_to(skill_dir) for f in skill_dir.rglob("*") if f.is_file()
    )
    combined = b"\n".join(
        f"{str(rel).replace(chr(92), '/')}".encode() + b"\0" + sha256_file(skill_dir / rel).encode()
        for rel in files
    )
    return "sha256:" + hashlib.sha256(combined).hexdigest(), [str(rel).replace("\\", "/") for rel in files]


def get_git_tree_sha(repo: Path, skill_path: Path) -> str:
    rel = skill_path.relative_to(repo)
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%T", "--", str(rel)],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def get_skill_versions(repo: Path, skill_dir: Path) -> dict:
    """Walk git log for the skill's meta.json; record each version's tree SHA + release date."""
    meta_rel = (skill_dir / "meta.json").relative_to(repo)
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse", "--format=%H %cI", "--", str(meta_rel)],
        capture_output=True, text=True
    )
    versions = {}
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        commit_sha, released = line.split(maxsplit=1)
        show = subprocess.run(
            ["git", "-C", str(repo), "show", f"{commit_sha}:{meta_rel}"],
            capture_output=True, text=True
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
            "released": released,
        }
    return versions


def get_commit_timestamp(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%cI", "HEAD"],
        capture_output=True, text=True
    )
    return result.stdout.strip() or "1970-01-01T00:00:00Z"


def get_provenance(repo: Path, skill_dir: Path) -> dict:
    rel = skill_dir.relative_to(repo)
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%cI %s", "--", str(rel)],
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
    prov: dict = {"merged_at": merged_at, "reviewed_by": "samuelgudi"}
    if pr_match is not None:
        prov["submitted_pr"] = pr_match
    return prov


def build_skill_entry(repo: Path, skill_dir: Path, status: str) -> dict:
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    fm = parse_frontmatter(skill_dir / "SKILL.md")
    content_hash, files = compute_content_hash(skill_dir)
    has_scripts = (skill_dir / "scripts").is_dir()
    # Derive skill id from directory path: <author_dir>/<slug_dir>
    author_name = skill_dir.parent.name
    slug_name = skill_dir.name
    skill_id = f"{author_name}/{slug_name}"
    versions = get_skill_versions(repo, skill_dir) or {
        meta["version"]: {
            "sha": get_git_tree_sha(repo, skill_dir),
            "released": get_commit_timestamp(repo),
        }
    }
    return {
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
        current = reg_path.read_text(encoding="utf-8") if reg_path.exists() else ""
        if current != serialized:
            print("registry.json out of sync. Run generate_manifest.py to regenerate.")
            return 1
        return 0
    reg_path.write_text(serialized, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
