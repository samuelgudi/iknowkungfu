# REVIEW.md - kriptoburak/hermes-tweet@0.1.0

## What does it do?
Use this skill when a Hermes Agent needs X/Twitter automation through Hermes Tweet: search tweets, read replies, look up users, export followers, monitor tweets, post tweets or replies, send DMs, and manage approval-gated X actions via Xquik.

## What does it access?

- Network endpoints: https://github.com/Xquik-dev/hermes-tweet, https://docs.xquik.com/guides/hermes-tweet, https://pypi.org/project/hermes-tweet/, and Xquik API endpoints under https://xquik.com/api/v1/ when the installed Hermes Tweet plugin is used.
- Filesystem paths: none from this instructions-only skill.
- Environment variables: XQUIK_API_KEY.
- Processes spawned: none from this instructions-only skill.

## Worst case if compromised?
This submission contains only SKILL.md and meta.json, with no scripts, templates, or executable assets. If the instructions were maliciously changed, they could mislead an agent into unsafe X/Twitter actions or credential handling. The current text explicitly forbids credential collection and requires approval before write-like X actions.

## Why is this useful?
I Know Kung Fu has Hermes-compatible registry and install adapters but no X/Twitter automation skill. Hermes Tweet fills that gap for Hermes Agent users who need concrete tweet search, reply reading, user lookup, follower export, monitoring, posting, replies, DMs, and approval-gated X actions through Xquik. Existing registry skills cover registry discovery, contribution, and semver decisions, not social/X workflows.

## Test evidence
Instructions-only skill. Validation run locally:

```bash
python3 scripts/validate.py submitted/kriptoburak-hermes-tweet/kriptoburak/hermes-tweet
python3 scripts/security_scan.py submitted/kriptoburak-hermes-tweet/kriptoburak/hermes-tweet --json
```

## What changed?
First-version submission.
