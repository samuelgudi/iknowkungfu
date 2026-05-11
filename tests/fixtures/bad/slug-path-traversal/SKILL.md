---
name: path-traversal-skill
description: Bad fixture — slug contains path-traversal sequence. Use only to test validate.py slug-grammar rejection.
---

# Slug Path Traversal

Violates rule: slug must match ^[a-z][a-z0-9-]{0,38}[a-z0-9]$ (no path separators or dots).
