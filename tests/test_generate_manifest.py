import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
GEN = ROOT / "scripts" / "generate_manifest.py"


def run_gen(cwd, *args):
    return subprocess.run([sys.executable, str(GEN), *args], cwd=cwd, capture_output=True, text=True)


def setup_test_repo(tmp_path):
    """Copy a minimal good fixture into a tmpdir + git init."""
    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "tests", "skills"))
    skill = repo / "skills" / "test-author" / "example"
    shutil.copytree(ROOT / "tests/fixtures/good/instructions-only", skill, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "test commit"], cwd=repo, check=True, capture_output=True)
    return repo


def test_generates_registry_json(tmp_path):
    repo = setup_test_repo(tmp_path)
    result = run_gen(repo)
    assert result.returncode == 0
    reg = json.loads((repo / "registry.json").read_text())
    assert reg["schema_version"] == 2
    assert len(reg["skills"]) == 1
    s = reg["skills"][0]
    assert s["id"] == "test-author/example"
    assert "source" in s and "content_hash" in s["source"]
    assert "versions" in s and "0.1.0" in s["versions"]


def test_deterministic(tmp_path):
    repo = setup_test_repo(tmp_path)
    run_gen(repo)
    first = (repo / "registry.json").read_bytes()
    run_gen(repo)
    second = (repo / "registry.json").read_bytes()
    assert first == second


def test_check_mode_passes_on_synced(tmp_path):
    repo = setup_test_repo(tmp_path)
    run_gen(repo)
    result = run_gen(repo, "--check")
    assert result.returncode == 0


def test_check_mode_fails_on_skill_drift(tmp_path):
    """Drift in the skills array (the canonical, version-stable content) fails --check.
    Tampering only with generated_at does NOT fail — that field is intentionally
    excluded from --check because it reflects HEAD's commit time and necessarily
    changes on every commit. See generate_manifest.py::main for the rationale."""
    repo = setup_test_repo(tmp_path)
    run_gen(repo)
    reg_path = repo / "registry.json"
    data = json.loads(reg_path.read_text())
    # Tamper a real content field: change the skill's version
    data["skills"][0]["version"] = "9.9.9"
    reg_path.write_text(json.dumps(data))
    result = run_gen(repo, "--check")
    assert result.returncode == 1


def test_check_mode_ignores_generated_at_drift(tmp_path):
    """generated_at is excluded from --check; tampering with it must NOT fail."""
    repo = setup_test_repo(tmp_path)
    run_gen(repo)
    reg_path = repo / "registry.json"
    data = json.loads(reg_path.read_text())
    data["generated_at"] = "1999-01-01T00:00:00Z"
    reg_path.write_text(json.dumps(data))
    result = run_gen(repo, "--check")
    assert result.returncode == 0


def test_schema_valid(tmp_path):
    """Generated registry.json must validate against scripts/schema.json."""
    import jsonschema

    repo = setup_test_repo(tmp_path)
    result = run_gen(repo)
    assert result.returncode == 0, result.stderr
    reg = json.loads((repo / "registry.json").read_text())
    schema = json.loads((ROOT / "scripts" / "schema.json").read_text())
    # raises jsonschema.ValidationError on failure
    jsonschema.validate(instance=reg, schema=schema)
