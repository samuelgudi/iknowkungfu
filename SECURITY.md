# SECURITY.md

## Threat model

The agent-skills registry distributes executable content — skills may include scripts that run with the user's credentials and filesystem access. The primary threat is **post-merge supply-chain compromise**: a skill passes review, is merged, and a subsequent update (or a dependency it fetches at runtime) introduces malicious behaviour. The pipeline defends against this by banning runtime package-manager installs (`PKG-INSTALL` hard block), binding author identity to an immutable GitHub numeric ID, and requiring explicit capability disclosure in REVIEW.md so reviewers can cross-check claims against actual code at every PR.

---

## Reviewer checklist

For every contribution PR, verify the following in order:

1. **Read REVIEW.md → match claims against actual code.** "What does it access?" and "What does it access → Network endpoints / Filesystem paths / Env vars / Processes spawned" must correspond to what the code actually does. Spot-check the highest-risk claims.

2. **Inspect SANITIZATION.diff → did sanitization quietly add anything?** The diff must only show removals or innocuous path normalisations. Any addition — especially to `scripts/` — is a red flag requiring explicit justification.

3. **Inspect `scan_results.json` → all hard-block counts are zero; every warning is acknowledged in REVIEW.md.** Soft warnings (`PY-SUBPROCESS-USE`, `FS-WRITE-OUTSIDE-SKILL`, `UNDECLARED-CMD`, `NET-IN-SCRIPT`) must each have a corresponding line in REVIEW.md explaining why they are safe. An unacknowledged warning is a blocker.

4. **For `has_scripts: true` PRs: line-by-line script review.** Verify that:
   - The capability declarations in REVIEW.md ("What does it access?") account for every network call, filesystem write, env var read, and subprocess spawn found in the code.
   - Real test evidence is present in REVIEW.md — actual commands run and actual outputs, not a description of what would happen. "Agent-only execution" is not an exemption (Decision #5).

5. **For new authors: verify `github_id` was fetched fresh.** The PR body must include the GitHub-ID verification result ("First-PR for new author; recorded github_id=XXXXXXXX"). Cross-check by running `gh api users/<github_login>` and confirming `id` matches `meta.json.author.github_id`. A mismatch means the username was re-registered to a different person.

6. **For yank PRs: verify the version exists and the reason is concrete.** The yanked version must appear in `registry.json.skills[].versions`. `yank_reason` must describe the actual compromise — a generic "security issue" is insufficient. See **Yank procedure** below.

---

## Reporting a vulnerability

Report vulnerabilities privately to **samuel.gudi.official@gmail.com** — do NOT open a public GitHub issue. Include: skill ID and version (if applicable), a reproduction path, and the impact you observed. You will receive acknowledgement within 48 hours. If the vulnerability is confirmed, the affected version will be yanked within 24 hours of confirmation.

---

## Yank procedure

Yanking marks a specific skill version as compromised. Yanked versions cannot be installed — there is no override flag (Decision #10).

1. Run `agent-skills yank <author>/<slug>@<version> --reason "..."` — the reason must be concrete (e.g., "Compromised upstream dependency in scripts/search.py; users must upgrade to 0.2.0+"). This appends an entry to `yanks.json` and opens a PR.
2. Review the PR: confirm the version exists in `registry.json`; confirm `yank_reason` is non-empty and specific.
3. Merge the PR.
4. Verify the merged state: `registry.json.skills[<id>].versions[<version>].yanked` must be `true` and `yank_reason` must be populated. `generate_manifest.py` performs this merge automatically on every regeneration — yanks are append-only.

If all versions of a skill are yanked, `agent-skills install <id>` hard-refuses with no override. Users who want to inspect the source for forensic purposes must use `--include-archived` manually, not install it.
