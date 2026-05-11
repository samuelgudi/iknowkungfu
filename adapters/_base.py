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
    marker = {
        "id": skill_id,
        "version": version,
        "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "installed_by": "agent-skills 0.1.0",
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


def compute_dir_content_hash(directory: Path) -> str:
    files = sorted(f for f in directory.rglob("*") if f.is_file() and f.name != MARKER_FILENAME)
    h = hashlib.sha256()
    for f in files:
        rel = str(f.relative_to(directory)).replace("\\", "/")
        h.update(rel.encode())
        h.update(b"\0")
        h.update(hashlib.sha256(f.read_bytes()).hexdigest().encode())
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
