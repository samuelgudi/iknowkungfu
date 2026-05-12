"""~/.cache/iknowkungfu/ helpers."""
import json
from pathlib import Path


def cache_dir() -> Path:
    d = Path.home() / ".cache/iknowkungfu"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_registry() -> dict | None:
    p = cache_dir() / "registry.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def db_path() -> Path:
    """Path to the FTS5 index derived from registry.json."""
    return cache_dir() / "registry.db"
