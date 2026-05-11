---
name: github-id-mismatch-skill
description: Bad fixture — meta.json github_id does not match what gh api returns. Use only to test github-id-mismatch detection in validate.py.
---

# Github Id Mismatch

meta.json declares `github_id: 99999999` but the fake_gh fixture returns `{"id": 12345678}`.
