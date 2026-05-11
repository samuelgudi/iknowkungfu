---
name: yank-no-reason-skill
description: Bad fixture — stub skill used with a yanks.json entry that has an empty reason field. Use only to test yank-validation in validate.py / generate_manifest.py.
---

# Yank No Reason

This skill itself is valid. The violation is exercised at test setup: a `yanks.json` entry referencing this skill's id has `"reason": ""` (empty string).

See README.md for the yanks.json entry to inject in tests.
