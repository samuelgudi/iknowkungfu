"""Integration test for Finding 5: install -> verify must report 'clean'.
Pre-fix this returned 'drift' on every install because generate_manifest and
adapters._base used divergent hash algorithms. Post-fix, they share one
canonical function — this test prevents that class of bug from re-entering."""
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent


def _build_registry_repo(tmp_path):
    """Build a tmp registry-repo with one skill from the good fixture."""
    repo = tmp_path / "registry-repo"
    shutil.copytree(ROOT, repo,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "tests"))
    # Replace skills/ with a single fixture skill.
    skills_root = repo / "skills"
    if skills_root.exists():
        shutil.rmtree(skills_root)
    skill_src = ROOT / "tests/fixtures/good/instructions-only"
    skill_dst = repo / "skills/test-author/example"
    skill_dst.mkdir(parents=True)
    shutil.copytree(skill_src, skill_dst, dirs_exist_ok=True)
    # Ensure the fixture's meta.json id matches our author/slug
    meta = json.loads((skill_dst / "meta.json").read_text(encoding="utf-8"))
    meta["id"] = "test-author/example"
    meta.setdefault("author", {})
    meta["author"]["github_login"] = "test-author"
    meta["author"]["github_id"] = 1
    (skill_dst / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, capture_output=True)
    # Generate registry.json
    subprocess.run([sys.executable, str(repo / "scripts/generate_manifest.py")],
                   cwd=repo, check=True, capture_output=True)
    return repo


def test_install_then_verify_clean(tmp_path, monkeypatch):
    """Full pipeline: generate_manifest builds registry.json with content_hash;
    install materializes the tree, writes the marker (which stores the SAME
    hash); verify recomputes from disk and compares. All three operations
    must produce identical bytes for the same content."""
    repo = _build_registry_repo(tmp_path)

    # Set up fake HOME with .claude and the registry/repo in the cache.
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    shutil.copy(repo / "registry.json", cache / "registry.json")
    shutil.copytree(repo, cache / "registry-repo")

    # Run install.
    from agent_skills.verbs.install import run as install_run
    class IArgs:
        spec = "test-author/example"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = install_run(IArgs())
    assert rc == 0, "install must succeed"
    target = home / ".claude/skills/test-author-example"
    assert (target / "SKILL.md").exists()
    assert (target / ".agent-skills-marker.json").exists()

    # Run verify — MUST return clean.
    from agent_skills.verbs.verify import run as verify_run
    class VArgs:
        id = "test-author/example"; agent = "claude-code"; json = True; yes = False
    rc = verify_run(VArgs())
    assert rc == 0, "verify --json always returns 0; status must be 'clean' in payload"

    # Sanity-check: marker's hash == registry's hash == on-disk hash.
    marker = json.loads((target / ".agent-skills-marker.json").read_text(encoding="utf-8"))
    registry = json.loads((cache / "registry.json").read_text(encoding="utf-8"))
    registry_hash = registry["skills"][0]["source"]["content_hash"]
    assert marker["registry_content_hash"] == registry_hash

    from adapters._base import compute_dir_content_hash
    on_disk_hash = compute_dir_content_hash(target)
    assert on_disk_hash == registry_hash, (
        f"on-disk recomputed hash diverges from registry hash — "
        f"this is exactly Finding 5 re-emerging. "
        f"on_disk={on_disk_hash!r} registry={registry_hash!r}"
    )


def test_uninstall_without_force_succeeds_after_install(tmp_path, monkeypatch):
    """Pre-Finding-5, uninstall-without-force failed on every install because
    every install reported drift. Post-fix, the happy path works. Regression
    guard so this never re-breaks."""
    repo = _build_registry_repo(tmp_path)

    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    shutil.copy(repo / "registry.json", cache / "registry.json")
    shutil.copytree(repo, cache / "registry-repo")

    from agent_skills.verbs.install import run as install_run
    class IArgs:
        spec = "test-author/example"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = install_run(IArgs())
    assert rc == 0, "install must succeed"

    from agent_skills.verbs.uninstall import run as uninstall_run
    class UArgs:
        id = "test-author/example"
        agent = "claude-code"
        force = False
        json = False
        yes = True
    rc = uninstall_run(UArgs())
    assert rc == 0
    target = home / ".claude/skills/test-author-example"
    assert not target.exists()
