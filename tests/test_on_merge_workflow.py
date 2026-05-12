"""Structural tests for .github/workflows/on-merge.yml.

These lock in the workflow ordering that the registry's install pipeline depends on:
the promotion (skill files moved into skills/) must be committed BEFORE the manifest
is regenerated, otherwise `git log -- skills/<author>/<slug>/meta.json` returns no
history and `generate_manifest.py` emits an empty versions[v].sha — which breaks
install with `git archive :<path>` (empty ref).
"""
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "on-merge.yml"


def _step_names() -> list[str]:
    spec = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = spec["jobs"]["promote"]["steps"]
    return [s.get("name", "") for s in steps]


def test_workflow_loads_as_yaml():
    spec = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert "jobs" in spec
    assert "promote" in spec["jobs"]


def test_commit_promotion_precedes_manifest_regen():
    """The "Commit promotion" step MUST appear before "Regenerate manifest". Without
    a commit at manifest-regen time, generate_manifest.py cannot find the skill's
    git history and emits an empty versions[v].sha — install breaks for the skill."""
    names = _step_names()
    try:
        commit_idx = names.index("Commit promotion")
    except ValueError:
        pytest.fail(f"No 'Commit promotion' step found. Steps: {names}")
    try:
        regen_idx = names.index("Regenerate manifest")
    except ValueError:
        pytest.fail(f"No 'Regenerate manifest' step found. Steps: {names}")
    assert commit_idx < regen_idx, (
        f"'Commit promotion' (step {commit_idx}) must come BEFORE "
        f"'Regenerate manifest' (step {regen_idx}). Current order: {names}"
    )


def test_promotion_step_does_not_commit():
    """The 'Promote each submitted dir' step must NOT contain `git commit`. Committing
    the promotion + manifest in one step recreates the empty-sha bug because the
    manifest regen would run before the commit."""
    spec = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = spec["jobs"]["promote"]["steps"]
    promote = next((s for s in steps if s.get("name") == "Promote each submitted dir"), None)
    assert promote is not None, "Promote step missing"
    assert "git commit" not in promote.get("run", ""), (
        "The 'Promote each submitted dir' step contains `git commit`, which would "
        "make the manifest regen run before a commit exists, producing empty sha."
    )
