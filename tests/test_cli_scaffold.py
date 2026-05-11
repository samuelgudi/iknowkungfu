import subprocess
import sys


def test_help_lists_verbs():
    result = subprocess.run(
        [sys.executable, "-m", "agent_skills", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    for verb in (
        "search", "show", "install", "uninstall", "verify",
        "list", "update", "init", "submit", "issue", "deprecate", "yank",
    ):
        assert verb in result.stdout, f"verb '{verb}' missing from help"
