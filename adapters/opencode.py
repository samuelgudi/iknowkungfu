"""OpenCode adapter (https://opencode.ai/docs/skills/).

OpenCode discovers skills from multiple paths (interoperable with Claude
Code and Codex). The canonical user path for OpenCode-managed skills is
`~/.config/opencode/skills/<name>/SKILL.md`. We target that location.

OpenCode enforces a constraint the other two agents do not:

> The skill folder name must match the `name` field in frontmatter.

The frontmatter `name` is also pattern-constrained:
> 1-64 chars, lowercase alphanumeric with single hyphen separators,
> no leading/trailing hyphen, no consecutive hyphens.

Because skill ids are `<author>/<slug>` but install folders share one
namespace, we use `<author>-<slug>` (flat) as the directory name AND
rewrite the SKILL.md frontmatter `name` to match. The pattern holds: a
valid GitHub login + valid skill slug yields `<github-login>-<slug>`,
each side already lowercase alphanumeric with single hyphens, joined by
exactly one hyphen — pattern-compliant.

Verify uses the marker's recorded registry_content_hash, not a recomputed
disk hash, since installation rewrites SKILL.md (same rationale as Hermes
and Codex adapters).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from adapters._base import (
    Adapter, InstallResult, UninstallResult, Installed, VerifyResult,
    write_marker, read_marker, atomic_install, checked_uninstall,
)
from adapters.codex import _rewrite_name_in_frontmatter, _flat


OPENCODE_USER_CONFIG = ".config/opencode"           # ~/.config/opencode/
OPENCODE_PROJECT_CONFIG = ".opencode"               # $CWD/.opencode/


class OpenCodeAdapter(Adapter):
    name = "opencode"

    def detect(self) -> bool:
        return (Path.home() / OPENCODE_USER_CONFIG).exists()

    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path:
        flat = _flat(skill_id)
        if scope == "project":
            return Path.cwd() / OPENCODE_PROJECT_CONFIG / "skills" / flat
        return Path.home() / OPENCODE_USER_CONFIG / "skills" / flat

    def install(self, src_dir: Path, skill_id: str, version: str, meta: dict, opts: dict) -> InstallResult:
        scope = opts.get("scope", "user")
        target = self.target_dir(skill_id, meta.get("category", "meta"), scope=scope)

        if target.exists() and read_marker(target) is None:
            return InstallResult(
                success=False, target=target, files_written=[],
                error=f"target {target} exists without marker — refuse to overwrite user-authored skill",
            )
        try:
            files_written = atomic_install(src_dir, target)
            _rewrite_name_in_frontmatter(target / "SKILL.md", _flat(skill_id))
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
        target = self.target_dir(skill_id, category="meta")
        return checked_uninstall(target, skill_id)

    def list_installed(self) -> list[Installed]:
        skills_dir = Path.home() / OPENCODE_USER_CONFIG / "skills"
        if not skills_dir.exists():
            return []
        result: list[Installed] = []
        for d in skills_dir.iterdir():
            marker = read_marker(d) if d.is_dir() else None
            if marker:
                result.append(Installed(id=marker["id"], version=marker["version"], target=d))
        return result

    def verify(self, skill_id: str, registry_hash: str, yanked: bool, yank_reason: str | None) -> VerifyResult:
        target = self.target_dir(skill_id, category="meta")
        if not target.exists():
            return VerifyResult(status="not_installed", message=f"{skill_id} not installed in opencode")
        marker = read_marker(target)
        if marker is None:
            return VerifyResult(status="no_marker", message="no marker — skill not managed by iknowkungfu")
        if yanked:
            return VerifyResult(
                status="yanked",
                message=f"version {marker['version']} YANKED: {yank_reason}. Uninstall recommended.",
            )
        if marker.get("registry_content_hash") != registry_hash:
            return VerifyResult(
                status="marker_outdated",
                message="marker hash differs from registry hash; reinstall may be needed",
            )
        return VerifyResult(
            status="clean",
            message=(
                f"{skill_id}@{marker['version']} marker matches registry "
                "(SKILL.md `name` field is host-renamed so disk hash differs from raw registry tree)"
            ),
        )
