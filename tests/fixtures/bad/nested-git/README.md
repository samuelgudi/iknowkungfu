# Bad fixture: nested-git

Violates rule: **nested git repository** — `.git/HEAD` is present directly inside the skill directory.

Note: the `.git/HEAD` file cannot be committed to a git repository (git silently ignores nested `.git` directories). Tests using this fixture must copy it to a tmp_path and create `.git/HEAD` there at setup time:

```python
import shutil
fixture_copy = tmp_path / "nested-git"
shutil.copytree(bad_fixture("nested-git"), fixture_copy)
(fixture_copy / ".git").mkdir()
(fixture_copy / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
```

Expected validation error: nested `.git` directory detected at skill root.
