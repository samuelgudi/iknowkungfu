"""OpenClaw adapter (https://docs.openclaw.ai/).

OpenClaw is a self-hosted gateway/personal AI assistant with a `openclaw`
CLI. Skill discovery paths:

    ~/.openclaw/skills/<name>/SKILL.md     ← canonical user-managed
    ~/.agents/skills/<name>/SKILL.md       ← shared "agents" namespace
    <workspace>/skills/<name>/SKILL.md     ← workspace-level (highest precedence)
    <workspace>/.agents/skills/<name>/SKILL.md

Detection signal: `~/.openclaw/` exists (the CLI's config home).

OpenClaw's frontmatter contract has one constraint the other adapters
don't: **`version` is required**, alongside `name` and `description`.
This adapter therefore injects `version` (from `meta.json`) into the
SKILL.md frontmatter alongside the `name` rewrite.

Slug pattern (from skill-format docs): `^[a-z0-9][a-z0-9-]*$`. Using
`<author>-<slug>` as the directory name satisfies this (each side already
lowercase alphanumeric with single hyphens).

The dir name does NOT have to equal the frontmatter `name` per OpenClaw
docs ("Slug derived from folder name by default"), but matching them
keeps adapters internally consistent.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from adapters._base import (
    Adapter, InstallResult, UninstallResult, Installed, VerifyResult,
    write_marker, read_marker, atomic_install, checked_uninstall,
)
from adapters.codex import _flat


def _rewrite_name_and_version(skill_md: Path, new_name: str, version: str) -> None:
    """Replace `name` and inject `version` in SKILL.md's YAML frontmatter,
    preserving description, body, and any other fields. OpenClaw requires
    all three (name, description, version) — without `version` the skill is
    rejected at load time."""
    text = skill_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md missing frontmatter — refusing to rewrite")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter not closed — refusing to rewrite")
    fm = yaml.safe_load(text[4:end]) or {}
    fm["name"] = new_name
    fm["version"] = version
    body = text[end + 5:]
    new_text = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n" + body
    skill_md.write_text(new_text, encoding="utf-8")


class OpenClawAdapter(Adapter):
    name = "openclaw"

    def detect(self) -> bool:
        return (Path.home() / ".openclaw").exists()

    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path:
        flat = _flat(skill_id)
        if scope == "project":
            # OpenClaw's workspace path is `<workspace>/skills/` (highest
            # precedence); we treat cwd as the workspace root.
            return Path.cwd() / "skills" / flat
        return Path.home() / ".openclaw" / "skills" / flat

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
            _rewrite_name_and_version(target / "SKILL.md", _flat(skill_id), version)
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
        skills_dir = Path.home() / ".openclaw" / "skills"
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
            return VerifyResult(status="not_installed", message=f"{skill_id} not installed in openclaw")
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
                "(SKILL.md frontmatter is host-rewritten — name + version — so disk hash differs from raw registry tree)"
            ),
        )
