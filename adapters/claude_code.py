"""Claude Code adapter."""
from __future__ import annotations

import shutil
from pathlib import Path

from adapters._base import (
    Adapter, InstallResult, UninstallResult, Installed, VerifyResult,
    write_marker, read_marker, atomic_install, compute_dir_content_hash,
    MARKER_FILENAME,
)


class ClaudeCodeAdapter(Adapter):
    name = "claude-code"

    def detect(self) -> bool:
        return (Path.home() / ".claude").exists()

    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path:
        author, slug = skill_id.split("/", 1)
        flat = f"{author}-{slug}"
        if scope == "project":
            return Path.cwd() / ".claude/skills" / flat
        return Path.home() / ".claude/skills" / flat

    def install(self, src_dir: Path, skill_id: str, version: str, meta: dict, opts: dict) -> InstallResult:
        category = meta.get("category", "meta")
        scope = opts.get("scope", "user")
        target = self.target_dir(skill_id, category, scope=scope)

        if target.exists() and read_marker(target) is None:
            return InstallResult(success=False, target=target, files_written=[],
                                 error=f"target {target} exists without marker — refuse to overwrite user-authored skill")
        try:
            files_written = atomic_install(src_dir, target)
            write_marker(
                target,
                skill_id=skill_id, version=version,
                content_hash=opts.get("registry_hash", ""),
                source_url=opts.get("source_url", ""),
                tree_sha=opts.get("tree_sha", ""),
            )
            return InstallResult(success=True, target=target, files_written=files_written)
        except Exception as e:
            if target.exists():
                shutil.rmtree(target)
            return InstallResult(success=False, target=target, files_written=[], error=str(e))

    def uninstall(self, skill_id: str) -> UninstallResult:
        author, slug = skill_id.split("/", 1)
        target = Path.home() / ".claude/skills" / f"{author}-{slug}"
        if not target.exists():
            return UninstallResult(success=False, target=target, error="not installed")
        if read_marker(target) is None:
            return UninstallResult(success=False, target=target, error="no marker — refusing to remove user-authored skill")
        shutil.rmtree(target)
        return UninstallResult(success=True, target=target)

    def list_installed(self) -> list[Installed]:
        skills_dir = Path.home() / ".claude/skills"
        if not skills_dir.exists():
            return []
        result = []
        for d in skills_dir.iterdir():
            marker = read_marker(d) if d.is_dir() else None
            if marker:
                result.append(Installed(id=marker["id"], version=marker["version"], target=d))
        return result

    def verify(self, skill_id: str, registry_hash: str, yanked: bool, yank_reason: str | None) -> VerifyResult:
        author, slug = skill_id.split("/", 1)
        target = Path.home() / ".claude/skills" / f"{author}-{slug}"
        if not target.exists():
            return VerifyResult(status="not_installed", message=f"{skill_id} not installed in claude-code")
        marker = read_marker(target)
        if marker is None:
            return VerifyResult(status="no_marker", message="no marker — skill not managed by agent-skills")
        actual_hash = compute_dir_content_hash(target)
        if yanked:
            return VerifyResult(status="yanked", message=f"version {marker['version']} YANKED: {yank_reason}. Uninstall recommended.")
        if actual_hash != registry_hash:
            return VerifyResult(status="drift", message=f"installed files differ from registry source hash for {skill_id}@{marker['version']}")
        return VerifyResult(status="clean", message=f"{skill_id}@{marker['version']} matches registry")
