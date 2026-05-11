"""install verb — resolve version, fetch tree, call adapter.install."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_skills.cache import load_registry, cache_dir
from agent_skills.detect import detect_host, get_adapter
from adapters._base import compute_dir_content_hash


def parse_spec(spec: str) -> tuple[str, str | None]:
    if "@" in spec:
        id_part, version = spec.split("@", 1)
        return id_part, version
    return spec, None


def find_skill(registry: dict, skill_id: str) -> dict | None:
    for s in registry.get("skills", []):
        if s["id"] == skill_id:
            return s
        # Also allow bare slug match if author is registry's default; for v0 require full id
    return None


def materialize_tree(repo_path: Path, tree_sha: str, source_subpath: str, staging: Path) -> None:
    """Use `git archive` to extract files at tree_sha:source_subpath into staging."""
    staging.mkdir(parents=True, exist_ok=True)
    # `git archive --format=tar <sha>:<path>` writes a tarball of that subtree to stdout.
    archive = subprocess.run(
        ["git", "-C", str(repo_path), "archive", "--format=tar", f"{tree_sha}:{source_subpath}"],
        check=True, capture_output=True,
    )
    import tarfile, io
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tf:
        tf.extractall(staging)


def resolve_install_id(registry: dict, raw_id: str) -> str | None:
    """If raw_id has author/slug shape, return as-is. Otherwise try bare-slug lookup.
    Returns the canonical `<author>/<slug>` id, or None."""
    if "/" in raw_id:
        return raw_id if find_skill(registry, raw_id) else None
    # Bare slug — try to find a unique match
    matches = [s["id"] for s in registry["skills"] if s["id"].split("/", 1)[1] == raw_id]
    if len(matches) == 1:
        return matches[0]
    return None


def run(args) -> int:
    registry = load_registry()
    if registry is None:
        print("Run `agent-skills update` first.", file=sys.stderr)
        return 1

    raw_id, version = parse_spec(args.spec)
    full_id = resolve_install_id(registry, raw_id)
    if full_id is None:
        print(f"Skill '{raw_id}' not found in registry. Try: agent-skills search {raw_id}", file=sys.stderr)
        return 1

    skill = find_skill(registry, full_id)

    if skill["status"] == "deprecated" and not getattr(args, "allow_deprecated", False):
        ssby = skill.get("superseded_by", "(none)")
        print(f"{full_id} is DEPRECATED, superseded by {ssby}.", file=sys.stderr)
        print("Use --allow-deprecated to install anyway.", file=sys.stderr)
        return 1

    versions = skill.get("versions", {})
    target_version = version or skill["version"]

    if target_version not in versions:
        available = ", ".join(sorted(versions.keys()))
        print(f"Version {target_version} not found. Available: {available}.", file=sys.stderr)
        return 1

    ver_info = versions[target_version]
    if ver_info.get("yanked", False):
        reason = ver_info.get("yank_reason", "(no reason given)")
        print(f"{full_id}@{target_version} was YANKED: {reason}.", file=sys.stderr)
        print("Yanked versions cannot be installed. No override flag exists.", file=sys.stderr)
        non_yanked = [v for v, info in versions.items() if not info.get("yanked")]
        if non_yanked:
            print(f"Try: agent-skills install {full_id}@{sorted(non_yanked)[-1]}", file=sys.stderr)
        return 1

    tree_sha = ver_info["sha"]
    source_path = skill.get("source", {}).get("path", f"skills/{full_id}")

    repo = cache_dir() / "registry-repo"
    if not (repo / ".git").exists():
        print(f"No registry repo at {repo}. Run `agent-skills update` first.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "staging"
        try:
            materialize_tree(repo, tree_sha, source_path, staging)
        except subprocess.CalledProcessError as e:
            print(f"git archive failed for tree {tree_sha}:{source_path}: {e}", file=sys.stderr)
            return 1

        content_hash = compute_dir_content_hash(staging)

        agent = detect_host(override=args.agent)
        adapter = get_adapter(agent)
        meta = json.loads((staging / "meta.json").read_text(encoding="utf-8"))
        result = adapter.install(
            staging, full_id, target_version,
            meta=meta,
            opts={
                "registry_hash": content_hash,
                "source_url": f"git+{repo}@{tree_sha}",
                "tree_sha": tree_sha,
                "scope": getattr(args, "scope", "user"),
            },
        )
        if not result.success:
            print(f"Install failed: {result.error}", file=sys.stderr)
            return 1

        if getattr(args, "json", False):
            print(json.dumps({
                "installed": True, "id": full_id, "version": target_version,
                "target": str(result.target), "files": result.files_written,
            }, indent=2))
        else:
            print(f"Installed {full_id}@{target_version} at {result.target}")
        return 0
