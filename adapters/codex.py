"""OpenAI Codex CLI adapter.

Codex (https://developers.openai.com/codex/skills) discovers skills in four
scopes; we target the two stable ones agent-skills cares about:

- user scope:    ~/.agents/skills/<name>/SKILL.md
- project scope: $CWD/.agents/skills/<name>/SKILL.md

The `.agents/skills/` namespace is a shared "agents" convention — OpenCode
also reads it. To avoid two-author collisions in that shared dir, we install
under `<author>-<slug>` (flat) instead of just `<slug>`. The Codex docs do
not require `folder name == frontmatter name`, but OpenCode (which also
reads `~/.agents/skills/`) does — so we rewrite the SKILL.md frontmatter's
`name` field to match the flat directory name. The original semantic name
remains in `meta.json` (`id: <author>/<slug>`).

Because we mutate SKILL.md, the installed disk hash necessarily differs
from the registry's content hash. `verify` therefore uses the marker's
`registry_content_hash` (Hermes-style), not a recomputed disk hash.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from adapters._base import (
    Adapter, InstallResult, UninstallResult, Installed, VerifyResult,
    write_marker, read_marker, atomic_install,
)


CODEX_CONFIG_DIR_NAME = ".codex"   # Codex CLI's own config home — detection signal
CODEX_SKILLS_DIR_NAME = ".agents/skills"  # Where Codex (and OpenCode) read user skills


def _rewrite_name_in_frontmatter(skill_md: Path, new_name: str) -> None:
    """Replace only the `name` field in SKILL.md's YAML frontmatter, preserving
    everything else (description, body, formatting of unrelated fields)."""
    text = skill_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md missing frontmatter — refusing to rewrite name")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter not closed — refusing to rewrite name")
    fm = yaml.safe_load(text[4:end]) or {}
    fm["name"] = new_name
    body = text[end + 5:]
    new_text = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n" + body
    skill_md.write_text(new_text, encoding="utf-8")


def _flat(skill_id: str) -> str:
    author, slug = skill_id.split("/", 1)
    return f"{author}-{slug}"


class CodexAdapter(Adapter):
    name = "codex"

    def detect(self) -> bool:
        return (Path.home() / CODEX_CONFIG_DIR_NAME).exists()

    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path:
        flat = _flat(skill_id)
        if scope == "project":
            return Path.cwd() / CODEX_SKILLS_DIR_NAME / flat
        return Path.home() / CODEX_SKILLS_DIR_NAME / flat

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
        skills_dir = Path.home() / CODEX_SKILLS_DIR_NAME
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
            return VerifyResult(status="not_installed", message=f"{skill_id} not installed in codex")
        marker = read_marker(target)
        if marker is None:
            return VerifyResult(status="no_marker", message="no marker — skill not managed by agent-skills")
        if yanked:
            return VerifyResult(
                status="yanked",
                message=f"version {marker['version']} YANKED: {yank_reason}. Uninstall recommended.",
            )
        # Codex install rewrites SKILL.md's `name` field for OpenCode-compatibility,
        # so disk hash diverges from the registry hash. Compare the marker's
        # recorded registry_content_hash instead (Hermes-style).
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
