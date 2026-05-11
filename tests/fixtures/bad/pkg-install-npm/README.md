# Bad fixture: pkg-install-npm

Violates rule: **runtime package install** — `scripts/setup.js` contains the string `npm install some-pkg`.

The security scanner (security_scan.py) pattern-matches against `npm install` in script files.

Expected validation error: runtime `npm install` detected in scripts.
