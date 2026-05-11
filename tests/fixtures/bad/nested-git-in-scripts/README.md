# Bad fixture: nested-git-in-scripts

Violates rule: **nested git repository in scripts/** — `scripts/.git/HEAD` is present inside the skill's scripts directory.

Note: the `scripts/.git/HEAD` file cannot be committed to a git repository (git silently ignores nested `.git` directories). Tests using this fixture must copy it to a tmp_path and create `scripts/.git/HEAD` there at setup time:

```python
import shutil
fixture_copy = tmp_path / "nested-git-in-scripts"
shutil.copytree(bad_fixture("nested-git-in-scripts"), fixture_copy)
(fixture_copy / "scripts" / ".git").mkdir(parents=True)
(fixture_copy / "scripts" / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
```

Expected validation error: nested `.git` directory detected under `scripts/`.
