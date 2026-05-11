"""Hermes adapter — category-based target, frontmatter synthesis."""
from __future__ import annotations

import shutil
import yaml
from pathlib import Path

from adapters._base import (
    Adapter, InstallResult, UninstallResult, Installed, VerifyResult,
    write_marker, read_marker, atomic_install, compute_dir_content_hash,
)


def synthesize_hermes_frontmatter(meta: dict, fm_name: str, fm_description: str) -> dict:
    fm = {
        "name": fm_name,
        "description": fm_description,
        "version": meta["version"],
        "author": f"{meta['author']['name']} ({meta['author']['github_login']})",
        "license": meta["license"],
    }
    if meta.get("platforms"):
        fm["platforms"] = meta["platforms"]
    if meta.get("requires"):
        fm["prerequisites"] = {
            "env_vars": meta["requires"].get("env_vars", []),
            "commands": meta["requires"].get("commands", []),
        }
    hermes_meta = {}
    if meta.get("tags"):
        hermes_meta["tags"] = meta["tags"]
    if meta.get("related_skills"):
        hermes_meta["related_skills"] = meta["related_skills"]
    if hermes_meta:
        fm["metadata"] = {"hermes": hermes_meta}
    return fm


def rewrite_skill_md(path: Path, new_fm: dict) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        body = text
    else:
        end = text.find("\n---\n", 4)
        body = text[end + 5:]
    new_text = "---\n" + yaml.safe_dump(new_fm, sort_keys=False) + "---\n" + body
    path.write_text(new_text, encoding="utf-8")


class HermesAdapter(Adapter):
    name = "hermes"

    def detect(self) -> bool:
        return (Path.home() / ".hermes").exists()

    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path:
        _, slug = skill_id.split("/", 1)
        return Path.home() / ".hermes/skills" / category / slug

    def install(self, src_dir: Path, skill_id: str, version: str, meta: dict, opts: dict) -> InstallResult:
        target = self.target_dir(skill_id, meta["category"])
        if target.exists() and read_marker(target) is None:
            return InstallResult(success=False, target=target, files_written=[],
                                 error=f"target {target} exists without marker — refuse to overwrite")
        try:
            files_written = atomic_install(src_dir, target)
            # Synthesize frontmatter in installed SKILL.md
            skill_md = target / "SKILL.md"
            import yaml as _yaml
            text = skill_md.read_text(encoding="utf-8")
            # Strip CRLF (Windows may produce it on copy)
            text = text.replace("\r\n", "\n")
            end = text.find("\n---\n", 4)
            existing_fm = _yaml.safe_load(text[4:end])
            new_fm = synthesize_hermes_frontmatter(meta, existing_fm["name"], existing_fm["description"])
            rewrite_skill_md(skill_md, new_fm)
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
        skills_dir = Path.home() / ".hermes/skills"
        if not skills_dir.exists():
            return UninstallResult(success=False, target=skills_dir, error="hermes skills dir not present")
        _, slug = skill_id.split("/", 1)
        for cat in skills_dir.iterdir():
            t = cat / slug
            if t.exists() and read_marker(t):
                m = read_marker(t)
                if m["id"] == skill_id:
                    shutil.rmtree(t)
                    return UninstallResult(success=True, target=t)
        return UninstallResult(success=False, target=skills_dir, error="not found")

    def list_installed(self) -> list[Installed]:
        skills_dir = Path.home() / ".hermes/skills"
        if not skills_dir.exists():
            return []
        result = []
        for cat in skills_dir.iterdir():
            if not cat.is_dir():
                continue
            for d in cat.iterdir():
                m = read_marker(d) if d.is_dir() else None
                if m:
                    result.append(Installed(id=m["id"], version=m["version"], target=d))
        return result

    def verify(self, skill_id: str, registry_hash: str, yanked: bool, yank_reason: str | None) -> VerifyResult:
        skills_dir = Path.home() / ".hermes/skills"
        _, slug = skill_id.split("/", 1)
        target = None
        for cat in skills_dir.iterdir() if skills_dir.exists() else []:
            t = cat / slug
            if t.exists() and read_marker(t) and read_marker(t)["id"] == skill_id:
                target = t
                break
        if target is None:
            return VerifyResult(status="not_installed", message=f"{skill_id} not installed in hermes")
        marker = read_marker(target)
        if yanked:
            return VerifyResult(status="yanked", message=f"version {marker['version']} YANKED: {yank_reason}. Uninstall recommended.")
        if marker.get("registry_content_hash") != registry_hash:
            return VerifyResult(status="marker_outdated", message=f"marker hash differs from registry hash; reinstall may be needed")
        return VerifyResult(status="clean", message=f"{skill_id}@{marker['version']} marker matches registry (Hermes frontmatter is host-synthesized so hash differs from raw registry tree)")
