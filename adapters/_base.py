"""Adapter ABC + shared install/uninstall mechanics."""
from __future__ import annotations

import abc
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


MARKER_FILENAME = ".agent-skills-marker.json"

# File extensions and bare names we treat as text — these get CRLF->LF
# normalisation before hashing so a Windows checkout (autocrlf=true) produces
# the same content_hash as a Linux checkout. The set mirrors the one in
# scripts/generate_manifest.py prior to v0.1.1; both files now import from
# here so the rules cannot drift again.
_TEXT_SUFFIXES = frozenset({
    ".md", ".py", ".pyi", ".js", ".ts", ".mjs", ".sh", ".bash", ".zsh",
    ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg", ".ini", ".rst",
})
_TEXT_NAMES = frozenset({
    "SKILL.md", "skill.md", "README.md", "LICENSE", "CONTRIBUTING.md",
    "SECURITY.md", "SCHEMA.md",
})


@dataclass
class InstallResult:
    success: bool
    target: Path
    files_written: list[str]
    error: str | None = None


@dataclass
class UninstallResult:
    success: bool
    target: Path
    error: str | None = None


@dataclass
class Installed:
    id: str
    version: str
    target: Path


@dataclass
class VerifyResult:
    status: str  # "clean" | "drift" | "marker_outdated" | "yanked" | "tampered" | "deprecated"
    message: str


def write_marker(target: Path, *, skill_id: str, version: str, content_hash: str, source_url: str, tree_sha: str) -> None:
    from agent_skills import __version__ as _agent_skills_version
    marker = {
        "id": skill_id,
        "version": version,
        "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "installed_by": f"agent-skills {_agent_skills_version}",
        "registry_content_hash": content_hash,
        "source_url": source_url,
        "tree_sha": tree_sha,
    }
    (target / MARKER_FILENAME).write_text(json.dumps(marker, indent=2), encoding="utf-8")


def read_marker(target: Path) -> dict | None:
    m = target / MARKER_FILENAME
    if not m.exists():
        return None
    return json.loads(m.read_text(encoding="utf-8"))


def _sha256_file_normalised(p: Path) -> str:
    """Hash file bytes. For known text files normalise CRLF->LF first so
    hashes are platform-independent (Windows autocrlf produces CRLF in the
    working tree even when the repo stores LF). Binary files are hashed
    byte-exact — normalising them would corrupt any file whose payload
    legitimately contains \\r\\n (PNG signature, compressed streams, etc.)."""
    h = hashlib.sha256()
    data = p.read_bytes()
    if p.suffix.lower() in _TEXT_SUFFIXES or p.name in _TEXT_NAMES:
        data = data.replace(b"\r\n", b"\n")
    h.update(data)
    return h.hexdigest()


def compute_dir_content_hash(directory: Path) -> str:
    """Canonical content hash for a skill directory. Used by:
      - scripts/generate_manifest.py    -> registry.json[].source.content_hash
      - agent_skills/verbs/install.py    -> marker's registry_content_hash
      - adapters/claude_code.py::verify  -> recompute disk-state for drift

    Algorithm (locked -- changing this invalidates every existing marker):
      1. Walk all files under `directory`, exclude MARKER_FILENAME.
      2. Sort by POSIX-style relative-path string (forward slashes,
         case-sensitive byte order -- NOT WindowsPath case-folding).
      3. For each file: produce `<posix_rel>\\0<sha256_hex>\\n` where
         sha256 is over CRLF-normalised bytes for text files / raw bytes
         for binary files.
      4. Concatenate all entries, sha256 the result, prefix `sha256:`.
    """
    rels = sorted(
        str(f.relative_to(directory)).replace("\\", "/")
        for f in directory.rglob("*")
        if f.is_file() and f.name != MARKER_FILENAME
    )
    h = hashlib.sha256()
    for rel in rels:
        file_hash = _sha256_file_normalised(directory / rel)
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(file_hash.encode("ascii"))
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


def atomic_install(src_dir: Path, target: Path) -> list[str]:
    """Stage src into temp; rename into target; return list of written files (relative)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        staging = Path(tmp) / "staged"
        shutil.copytree(src_dir, staging)
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(staging), str(target))
    return sorted(str(f.relative_to(target)).replace("\\", "/") for f in target.rglob("*") if f.is_file())


class Adapter(abc.ABC):
    name: str

    @abc.abstractmethod
    def detect(self) -> bool: ...

    @abc.abstractmethod
    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path: ...

    @abc.abstractmethod
    def install(self, src_dir: Path, skill_id: str, version: str, meta: dict, opts: dict) -> InstallResult: ...

    @abc.abstractmethod
    def uninstall(self, skill_id: str) -> UninstallResult: ...

    @abc.abstractmethod
    def list_installed(self) -> list[Installed]: ...

    @abc.abstractmethod
    def verify(self, skill_id: str, registry_hash: str, yanked: bool, yank_reason: str | None) -> VerifyResult: ...
