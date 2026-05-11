# SECURITY.md

## Defenses in place

The following checks run automatically on every contribution PR and registry operation — reviewers do not need to manually replicate them:

- **`validate.py`** (`scripts/validate.py --all`): schema correctness, cross-file consistency, and cross-skill uniqueness checks. Runs in the `registry-checks` CI job on every push and PR.
- **`security_scan.py`** (`scripts/security_scan.py --all`): 8 hard-block rules + 4 soft-warn rules defined in `rules.yaml`. Hard blocks include `PKG-INSTALL`, `EXEC-ARBITRARY`, `OBFUSCATED-CODE`, and others. Runs in the `registry-checks` CI job.
- **Registry-anchored content hash**: every installed skill version carries a `content_hash` from `registry.json`. `adapter.verify()` recomputes the hash on install and refuses if it doesn't match.
- **Hard yank refusal**: yanked versions cannot be installed. There is no override flag (Decision #10). `agent-skills install` hard-refuses with no override even if the user passes `--force`.
- **Per-version GitHub-ID binding**: `meta.json.author.github_id` is the numeric GitHub user ID fetched at submit time. It is immutable after first registration. The `contribution-pr-check` CI job verifies the declared ID against the live `gh api users/<login>` response for new authors.

---

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

5. **For new authors: confirm the `contribution-pr-check` CI job passed.** The CI job (`GitHub-ID verification for new authors` step in `.github/workflows/ci.yml`) fetches the live numeric GitHub ID via `gh api users/<login>` and compares it to `meta.json.author.github_id`. A passing CI step means the IDs matched. Your manual job is to confirm CI passed — you do not need to re-run `gh api` yourself unless the CI result is ambiguous or the job was skipped.

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
