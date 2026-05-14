"""test_validate.py — TDD coverage for scripts/validate.py.

TDD order followed:
  Step 1: test_good_instructions_only_passes (initial seed)
  Step 5: test_bad_fixture_fails parametrized (basic single-skill rules)
  Step 7: extended coverage — all 18 bad fixtures, cross-skill cycles,
          github_id, nested-git, yank-no-reason, pkg-install-*, extraneous-file
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
VALIDATE = ROOT / "scripts" / "validate.py"
FIXTURES_BAD = ROOT / "tests" / "fixtures" / "bad"
FIXTURES_GOOD = ROOT / "tests" / "fixtures" / "good"


def run_validate(*args, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(VALIDATE), *args],
        capture_output=True, text=True, env=env
    )


# ---------------------------------------------------------------------------
# Step 1 / Step 4: Good fixtures must all pass
# ---------------------------------------------------------------------------

def test_good_instructions_only_passes():
    result = run_validate(str(FIXTURES_GOOD / "instructions-only"))
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"


@pytest.mark.parametrize("name", [
    "deprecated",
    "multi-agent",
    "multi-version",
    "with-scripts",
    "with-templates",
    "imported",
])
def test_good_fixture_passes(name):
    result = run_validate(str(FIXTURES_GOOD / name))
    assert result.returncode == 0, (
        f"Good fixture '{name}' unexpectedly failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Step 5 / Step 6: Basic single-skill bad fixtures (parametrized)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected_msg_substring", [
    ("slug-with-uppercase", "regex"),
    ("missing-license", "license"),
    ("deprecated-no-successor", "superseded_by"),
    ("tag-cap-exceeded", "tags count"),
    ("slug-path-traversal", "regex"),
    ("frontmatter-mismatch", "frontmatter name"),
])
def test_bad_fixture_fails(name, expected_msg_substring):
    result = run_validate(str(FIXTURES_BAD / name))
    assert result.returncode != 0, (
        f"Expected failure for '{name}'; got returncode=0.\nstdout: {result.stdout}"
    )
    assert expected_msg_substring in result.stdout, (
        f"Expected '{expected_msg_substring}' in output for '{name}', "
        f"got:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# Step 7: Extended bad-fixture coverage
# ---------------------------------------------------------------------------

# --- extraneous-file ----------------------------------------------------------

def test_extraneous_file_fails():
    result = run_validate(str(FIXTURES_BAD / "extraneous-file"))
    assert result.returncode != 0, f"Expected failure; stdout: {result.stdout}"
    assert "secrets.txt" in result.stdout, (
        f"Expected 'secrets.txt' in output, got:\n{result.stdout}"
    )


# --- nested-git (root) -------------------------------------------------------
# .git/HEAD cannot be committed; we copy the fixture and create it at runtime.

def test_nested_git_fails(tmp_path):
    src = FIXTURES_BAD / "nested-git"
    fixture_copy = tmp_path / "nested-git"
    shutil.copytree(str(src), str(fixture_copy))
    (fixture_copy / ".git").mkdir()
    (fixture_copy / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    result = run_validate(str(fixture_copy))
    assert result.returncode != 0, f"Expected failure; stdout: {result.stdout}"
    assert ".git" in result.stdout, (
        f"Expected '.git' in output, got:\n{result.stdout}"
    )


# --- nested-git-in-scripts ---------------------------------------------------

def test_nested_git_in_scripts_fails(tmp_path):
    src = FIXTURES_BAD / "nested-git-in-scripts"
    fixture_copy = tmp_path / "nested-git-in-scripts"
    shutil.copytree(str(src), str(fixture_copy))
    (fixture_copy / "scripts" / ".git").mkdir(parents=True)
    (fixture_copy / "scripts" / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    result = run_validate(str(fixture_copy))
    assert result.returncode != 0, f"Expected failure; stdout: {result.stdout}"
    assert ".git" in result.stdout, (
        f"Expected '.git' in output, got:\n{result.stdout}"
    )


# --- yank-no-reason ----------------------------------------------------------
# The fixture is valid on its own; the violation is injected via a yanks.json.

def test_yank_no_reason_fails(tmp_path):
    src = FIXTURES_BAD / "yank-no-reason"
    fixture_copy = tmp_path / "yank-no-reason"
    shutil.copytree(str(src), str(fixture_copy))
    yanks_file = tmp_path / "yanks.json"
    yanks_file.write_text(json.dumps({
        "yanks": [{
            "id": "test-author/yank-no-reason-skill",
            "version": "0.1.0",
            "yanked_at": "2026-05-11T00:00:00Z",
            "yanked_by": "test-author",
            "reason": ""
        }]
    }))
    result = run_validate(str(fixture_copy), "--yanks", str(yanks_file))
    assert result.returncode != 0, f"Expected failure; stdout: {result.stdout}"
    assert "reason" in result.stdout, (
        f"Expected 'reason' in output, got:\n{result.stdout}"
    )


# --- github-id-mismatch ------------------------------------------------------
# Uses fake_gh fixture from conftest.py. fake_gh returns id=12345678;
# the fixture declares github_id=99999999.

def test_github_id_mismatch_fails(fake_gh, tmp_path):
    # fake_gh conftest fixture creates a gh shim in a tmp bin/ directory and
    # patches PATH via monkeypatch.  On Windows, Python subprocess without
    # shell=True resolves .exe before .bat even when the .bat dir is earlier in
    # PATH.  We pass the patched PATH explicitly to run_validate so the child
    # process picks up the shim's directory first via PATHEXT ordering.
    # The shim returns {"id": 12345678, "login": "test-author"};
    # the fixture's meta.json declares github_id=99999999 — a mismatch.
    src = FIXTURES_BAD / "github-id-mismatch"
    fixture_copy = tmp_path / "github-id-mismatch"
    shutil.copytree(str(src), str(fixture_copy))

    # Locate the shim directory from fake_gh (parent of gh.log is tmp_path, bin/ is sibling)
    shim_bin = fake_gh["log"].parent / "bin"
    patched_path = str(shim_bin) + os.pathsep + os.environ.get("PATH", "")
    result = run_validate(
        str(fixture_copy), "--check-github-id",
        extra_env={"PATH": patched_path},
    )
    assert result.returncode != 0, (
        f"Expected failure for github-id-mismatch; stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "github_id" in result.stdout, (
        f"Expected 'github_id' in output, got:\n{result.stdout}"
    )


# --- Cross-skill: deprecated-cycle ------------------------------------------
# Pass both sub-fixtures together via --multi

def test_deprecated_cycle_fails(tmp_path):
    a = FIXTURES_BAD / "deprecated-cycle" / "a"
    b = FIXTURES_BAD / "deprecated-cycle" / "b"
    result = run_validate("--multi", str(a), str(b))
    assert result.returncode != 0, (
        f"Expected failure for deprecated-cycle; stdout: {result.stdout}"
    )
    combined = result.stdout + result.stderr
    assert "cycle" in combined.lower(), (
        f"Expected 'cycle' in output, got:\n{combined}"
    )


# --- Cross-skill: composes-cycle --------------------------------------------

def test_composes_cycle_fails(tmp_path):
    a = FIXTURES_BAD / "composes-cycle" / "a"
    b = FIXTURES_BAD / "composes-cycle" / "b"
    result = run_validate("--multi", str(a), str(b))
    assert result.returncode != 0, (
        f"Expected failure for composes-cycle; stdout: {result.stdout}"
    )
    combined = result.stdout + result.stderr
    assert "cycle" in combined.lower(), (
        f"Expected 'cycle' in output, got:\n{combined}"
    )


# --- Cross-skill: extends-cycle ---------------------------------------------

def test_extends_cycle_fails(tmp_path):
    a = FIXTURES_BAD / "extends-cycle" / "a"
    b = FIXTURES_BAD / "extends-cycle" / "b"
    result = run_validate("--multi", str(a), str(b))
    assert result.returncode != 0, (
        f"Expected failure for extends-cycle; stdout: {result.stdout}"
    )
    combined = result.stdout + result.stderr
    assert "cycle" in combined.lower(), (
        f"Expected 'cycle' in output, got:\n{combined}"
    )


# --- Cross-skill: same-slug-collision ----------------------------------------

def test_same_slug_collision_fails(tmp_path):
    a = FIXTURES_BAD / "same-slug-collision" / "author-x"
    b = FIXTURES_BAD / "same-slug-collision" / "author-y"
    result = run_validate("--multi", str(a), str(b))
    assert result.returncode != 0, (
        f"Expected failure for same-slug-collision; stdout: {result.stdout}"
    )
    combined = result.stdout + result.stderr
    assert "slug" in combined.lower() or "collision" in combined.lower(), (
        f"Expected slug/collision message, got:\n{combined}"
    )


# --- JSON output mode is valid JSON ------------------------------------------

def test_json_output_is_valid_json():
    result = run_validate(str(FIXTURES_GOOD / "instructions-only"), "--json")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, dict)


# --- --strict mode promotes warnings to errors -------------------------------

def test_strict_flag_exists():
    """Smoke-test: --strict flag doesn't crash."""
    result = run_validate(str(FIXTURES_GOOD / "instructions-only"), "--strict")
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"


# ---------------------------------------------------------------------------
# Imported skills: origin block validation + conditional LICENSE/NOTICE files
# (ADR-002 — import/curation provenance model)
# ---------------------------------------------------------------------------

# --- origin block missing a required sub-field -------------------------------

def test_origin_missing_field_fails():
    """An origin block missing a required sub-field (repo) must fail."""
    result = run_validate(str(FIXTURES_BAD / "origin-missing-field"))
    assert result.returncode != 0, f"Expected failure; stdout: {result.stdout}"
    assert "origin" in result.stdout and "repo" in result.stdout, (
        f"Expected an origin/repo message, got:\n{result.stdout}"
    )


# --- origin block with an unknown sub-field ----------------------------------

def test_origin_unknown_field_fails():
    """An origin block with an unknown sub-field (license) must fail."""
    result = run_validate(str(FIXTURES_BAD / "origin-unknown-field"))
    assert result.returncode != 0, f"Expected failure; stdout: {result.stdout}"
    assert "origin" in result.stdout and "license" in result.stdout, (
        f"Expected an origin/unknown-sub-field message, got:\n{result.stdout}"
    )


# --- LICENSE file present without an origin block ----------------------------

def test_license_file_without_origin_fails():
    """A bundled LICENSE file is only permitted for imported skills (those with
    an origin block). Without origin, it must be flagged as extraneous."""
    result = run_validate(str(FIXTURES_BAD / "license-file-not-imported"))
    assert result.returncode != 0, f"Expected failure; stdout: {result.stdout}"
    assert "LICENSE" in result.stdout, (
        f"Expected 'LICENSE' flagged as extraneous, got:\n{result.stdout}"
    )


# --- imported skill WITH origin may bundle a LICENSE file --------------------

def test_imported_skill_with_license_file_passes():
    """The good/imported fixture has an origin block and bundles a LICENSE
    file — that combination must be accepted."""
    result = run_validate(str(FIXTURES_GOOD / "imported"))
    assert result.returncode == 0, (
        f"Imported fixture with bundled LICENSE unexpectedly failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
