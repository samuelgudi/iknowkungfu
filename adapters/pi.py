"""Pi coding agent adapter (https://github.com/earendil-works/pi).

Pi (`@earendil-works/pi-coding-agent` on npm; binary: `pi`) is "a minimal
terminal coding harness". It scans these locations for skills:

    ~/.pi/agent/skills/<name>/SKILL.md   ← canonical user-managed
    ~/.agents/skills/<name>/SKILL.md     ← shared "agents" namespace (also Codex)
    $CWD/.pi/skills/<name>/SKILL.md      ← canonical project
    $CWD/.agents/skills/<name>/SKILL.md  ← shared "agents" namespace (also Codex)

Pi's config home is `~/.pi/agent/` (overridable via `PI_CODING_AGENT_DIR`).
That directory holds `settings.json`, `keybindings.json`, `AGENTS.md`,
`prompts/`, `extensions/`, `skills/`, `themes/`, `sessions/`. We use its
existence as the detection signal.

Pi accepts the same SKILL.md+frontmatter shape as Claude Code and Codex
(name + description). To stay consistent with the other multi-host adapters
that install under a shared dir (codex, opencode), we use `<author>-<slug>`
as the folder name and rewrite the SKILL.md `name` field to match.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from adapters._base import (
    Adapter, InstallResult, UninstallResult, Installed, VerifyResult,
    write_marker, read_marker, atomic_install,
)
from adapters.codex import _rewrite_name_in_frontmatter, _flat


def _pi_config_home() -> Path:
    """Honour PI_CODING_AGENT_DIR override per pi's own conventions; fall back
    to ~/.pi/agent."""
    env = os.environ.get("PI_CODING_AGENT_DIR")
    if env:
        return Path(env)
    return Path.home() / ".pi" / "agent"


class PiAdapter(Adapter):
    name = "pi"

    def detect(self) -> bool:
        return _pi_config_home().exists()

    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path:
        flat = _flat(skill_id)
        if scope == "project":
            return Path.cwd() / ".pi" / "skills" / flat
        return _pi_config_home() / "skills" / flat

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
        if not target.exists():
            return UninstallResult(success=False, target=target, error="not installed")
        if read_marker(target) is None:
            return UninstallResult(
                success=False, target=target,
                error="no marker — refusing to remove user-authored skill",
            )
        shutil.rmtree(target)
        return UninstallResult(success=True, target=target)

    def list_installed(self) -> list[Installed]:
        skills_dir = _pi_config_home() / "skills"
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
            return VerifyResult(status="not_installed", message=f"{skill_id} not installed in pi")
        marker = read_marker(target)
        if marker is None:
            return VerifyResult(status="no_marker", message="no marker — skill not managed by agent-skills")
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
