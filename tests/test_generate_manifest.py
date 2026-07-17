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


def test_generated_at_is_utc_z(tmp_path):
    """generated_at and versions[v].released must be normalized to UTC with Z
    suffix. Without this, manifests built on Windows (CEST) and GHA (UTC)
    differ in formatting, which the rollback guard mis-classifies as a
    rollback because of naive string comparison."""
    repo = setup_test_repo(tmp_path)
    result = run_gen(repo)
    assert result.returncode == 0, result.stderr
    reg = json.loads((repo / "registry.json").read_text())
    assert reg["generated_at"].endswith("Z"), (
        f"generated_at must end with 'Z', got: {reg['generated_at']!r}"
    )
    for skill in reg["skills"]:
        for ver, info in skill["versions"].items():
            assert info["released"].endswith("Z"), (
                f"versions[{ver}].released must end with 'Z', got: {info['released']!r}"
            )


def test_to_utc_z_normalizes_offsets():
    """Unit test for _to_utc_z. Locks the offset-stripping behaviour."""
    from scripts.generate_manifest import _to_utc_z
    assert _to_utc_z("2026-05-12T10:43:59+02:00") == "2026-05-12T08:43:59Z"
    assert _to_utc_z("2026-05-12T08:44:15Z") == "2026-05-12T08:44:15Z"
    assert _to_utc_z("2026-05-12T08:44:15+00:00") == "2026-05-12T08:44:15Z"
    # Naive timestamp: assume UTC (matches the rollback-guard parser).
    assert _to_utc_z("2026-05-12T08:44:15") == "2026-05-12T08:44:15Z"
    # Empty + malformed: pass-through.
    assert _to_utc_z("") == ""
    assert _to_utc_z("not-a-timestamp") == "not-a-timestamp"


def test_generate_manifest_uses_canonical_hash_function():
    """generate_manifest.py must NOT define its own compute_content_hash —
    it must import from adapters._base. Lock the architecture so a future
    contributor doesn't re-introduce the two-implementations bug."""
    import scripts.generate_manifest as gm
    import adapters._base as base
    # If both modules export the same function object, they share an
    # implementation. If they don't, this test is a no-op (false-negative
    # safe), but the test in test_hash_canonical.py
    # `test_generate_manifest_and_base_produce_equal_hashes` is the real gate.
    # This test just protects against a sneaky re-fork.
    assert not hasattr(gm, "compute_content_hash"), (
        "generate_manifest.compute_content_hash was removed in v0.1.1 — "
        "the canonical implementation lives in adapters._base. If you need "
        "to extend hashing semantics, edit adapters/_base.py only."
    )
    assert not hasattr(gm, "sha256_file"), (
        "generate_manifest.sha256_file was removed in v0.1.1 — see above."
    )


def test_origin_block_passes_through(tmp_path):
    """A skill with an origin block (imported skill, ADR-002) must carry that
    block through to registry.json verbatim. A first-party skill must NOT
    gain an origin key."""
    import jsonschema

    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", "*.egg-info", "tests", "skills"))
    shutil.copytree(ROOT / "tests/fixtures/good/instructions-only",
                    repo / "skills" / "test-author" / "example",
                    dirs_exist_ok=True)
    shutil.copytree(ROOT / "tests/fixtures/good/imported",
                    repo / "skills" / "test-author" / "imported-skill",
                    dirs_exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "test commit"], cwd=repo, check=True, capture_output=True)

    result = run_gen(repo)
    assert result.returncode == 0, result.stderr
    reg = json.loads((repo / "registry.json").read_text())
    skills = {s["id"]: s for s in reg["skills"]}

    imported = skills["test-author/imported-skill"]
    assert "origin" in imported, "imported skill must carry an origin block"
    assert imported["origin"] == {
        "author_name": "Original Author",
        "author_url": "https://github.com/original-author",
        "repo": "https://github.com/original-author/source-repo",
        "ref": "abc1234def5678",
        "imported_at": "2026-05-14T00:00:00Z",
    }

    first_party = skills["test-author/example"]
    assert "origin" not in first_party, (
        "first-party skill (no origin in meta.json) must not gain an origin key"
    )

    # The generated manifest, origin block included, must still be schema-valid.
    schema = json.loads((ROOT / "scripts" / "schema.json").read_text())
    jsonschema.validate(instance=reg, schema=schema)


def test_malformed_directory_name_refused(tmp_path):
    """A skill dir whose name violates the slug grammar must never be manifested."""
    repo = setup_test_repo(tmp_path)
    bad = repo / "skills" / "test-author" / "evil..name"
    shutil.copytree(ROOT / "tests/fixtures/good/instructions-only", bad)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add bad dir"], cwd=repo, check=True, capture_output=True)
    result = run_gen(repo)
    assert result.returncode != 0
    assert "grammar" in (result.stdout + result.stderr)
