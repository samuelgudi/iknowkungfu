# Bad fixture: pkg-install-pip

Violates rule: **runtime package install** — `scripts/setup.sh` contains `pip install some-pkg`.

Dependencies must be pre-declared in `requires.commands`, not installed at runtime.

Expected validation error: runtime `pip install` detected in scripts.
