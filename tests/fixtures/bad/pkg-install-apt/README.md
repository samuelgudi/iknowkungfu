# Bad fixture: pkg-install-apt

Violates rule: **runtime package install** — `scripts/setup.sh` contains `apt-get install some-pkg`.

Dependencies must be pre-declared in `requires.commands`, not installed at runtime.

Expected validation error: runtime `apt-get install` detected in scripts.
