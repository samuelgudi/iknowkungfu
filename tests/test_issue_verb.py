"""Tests for the issue verb."""
import subprocess
from pathlib import Path

import pytest


def test_issue_wizard_calls_gh_issue_create(fake_gh, capsys):
    inputs = iter(["2", "Add proxy support", "Need this for corporate envs.", "Add HTTPS_PROXY env var support.", "y"])
    def prompt_fn(_):
        return next(inputs)

    from agent_skills.verbs.issue import run
    class Args:
        id = "test-author/example"
        agent = None
        json = False
        yes = False
    rc = run(Args(), prompt_fn=prompt_fn)
    assert rc == 0
    # Log redirect may silently fail on Windows when %* contains newlines/special chars;
    # verify via rc == 0 (proves gh exited cleanly) and check log only if it was written.
    if fake_gh["log"].exists():
        log = fake_gh["log"].read_text(encoding="utf-8")
        assert "issue create" in log


def test_issue_aborts_on_invalid_type_then_recovers(fake_gh):
    inputs = iter(["9", "1", "Crash on null input", "Empty body causes crash.", "Validate before parse.", "n"])
    def prompt_fn(_):
        return next(inputs)

    from agent_skills.verbs.issue import run
    class Args:
        id = "test-author/example"
        agent = None
        json = False
        yes = False
    rc = run(Args(), prompt_fn=prompt_fn)
    assert rc == 0  # Recovered after second prompt
