---
name: license-file-not-imported-skill
description: Use this skill when exercising the license-file-not-imported bad fixture through validate.py.
---

# license-file-not-imported-skill

Fixture body. The directory bundles a LICENSE file but the meta.json has no
origin block — a bundled LICENSE is only permitted for imported skills, so
this must be rejected as an extraneous file.
