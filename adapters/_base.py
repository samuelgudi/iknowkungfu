"""Adapter ABC + shared install/uninstall mechanics."""
from __future__ import annotations

import abc
import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


MARKER_FILENAME = ".iknowkungfu-marker.json"

# Same grammar as scripts/validate.py ID_REGEX. Enforced before any path is
# built from a skill id — the components become directory names, so anything
# outside this grammar (e.g. "a/../../x") is a path-traversal attempt.
SKILL_ID_REGEX = re.compile(
    r"^[a-z][a-z0-9-]{0,38}[a-z0-9]/[a-z][a-z0-9-]{0,38}[a-z0-9]$"
)


def split_skill_id(skill_id: str) -> tuple[str, str]:
    """Validate '<author>/<slug>' against the registry grammar and split it.

    Raises ValueError on any id that fails the grammar. Every adapter MUST
    derive filesystem paths through this helper, never via a raw split.
    """
    if not SKILL_ID_REGEX.match(skill_id or ""):
        raise ValueError(
            f"invalid skill id {skill_id!r} — expected <author>/<slug> "
            f"matching the registry grammar"
        )
    author, slug = skill_id.split("/", 1)
    return author, slug

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
        "installed_by": f"iknowkungfu {_agent_skills_version}",
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
    """Stage src into temp; swap into target; return list of written files (relative).

    On reinstall the old tree is moved aside first, then the staged tree moves
    in, then the old tree is deleted — so an interruption anywhere leaves either
    the old install or the new one on disk, never a deleted target with nothing
    in its place (delete-then-move had exactly that window)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        staging = Path(tmp) / "staged"
        shutil.copytree(src_dir, staging)
        old = Path(tmp) / "replaced"
        if target.exists():
            shutil.move(str(target), str(old))
        try:
            shutil.move(str(staging), str(target))
        except BaseException:
            # Roll the previous install back into place before propagating.
            if old.exists() and not target.exists():
                shutil.move(str(old), str(target))
            raise
    return sorted(str(f.relative_to(target)).replace("\\", "/") for f in target.rglob("*") if f.is_file())


def checked_uninstall(target: Path, skill_id: str) -> UninstallResult:
    """Shared uninstall guard: only remove a directory that carries a marker
    whose id matches the requested skill_id. The marker-presence check alone
    is not enough — a crafted id could resolve to a *different* managed
    directory, and rmtree must never fire on a directory the caller didn't
    actually name."""
    if not target.exists():
        return UninstallResult(success=False, target=target, error="not installed")
    marker = read_marker(target)
    if marker is None:
        return UninstallResult(
            success=False, target=target,
            error="no marker — refusing to remove user-authored skill",
        )
    if marker.get("id") != skill_id:
        return UninstallResult(
            success=False, target=target,
            error=f"marker belongs to {marker.get('id')!r}, not {skill_id!r} — refusing to remove",
        )
    shutil.rmtree(target)
    return UninstallResult(success=True, target=target)


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
