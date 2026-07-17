# REVIEW.md - kriptoburak/hermes-tweet@0.1.6

## What does it do?
Use Xquik from Hermes Agent for X search, posting, replies, likes, retweets, follows, DMs, monitors, extraction jobs, draws, media, and trends.

## What does it access?

- Network endpoints: https://github.com/Xquik-dev/hermes-tweet, https://docs.xquik.com/guides/hermes-tweet, https://pypi.org/project/hermes-tweet/, and Xquik API endpoints under https://xquik.com/api/v1/ when the installed Hermes Tweet plugin is used.
- Filesystem paths: none from this instructions-only skill.
- Environment variables: XQUIK_API_KEY.
- Processes spawned: none from this instructions-only skill.

## Worst case if compromised?
This submission contains only SKILL.md and meta.json, with no scripts, templates, or executable assets. If the instructions were maliciously changed, they could mislead an agent into unsafe X/Twitter actions or credential handling. The current text explicitly forbids credential collection, keeps actions gated by `HERMES_TWEET_ENABLE_ACTIONS=true`, and requires approval before write-like X actions.

## Why is this useful?
I Know Kung Fu has Hermes-compatible registry and install adapters but no X/Twitter automation skill. Hermes Tweet fills that gap for Hermes Agent users who need concrete tweet search, reply reading, user lookup, follower export, monitoring, posting, replies, DMs, and approval-gated X actions through Xquik. Existing registry skills cover registry discovery, contribution, and semver decisions, not social/X workflows.

## Test evidence
Instructions-only skill. Validation run locally:

```bash
python3 scripts/validate.py submitted/kriptoburak-hermes-tweet/kriptoburak/hermes-tweet --check-github-id
python3 scripts/security_scan.py submitted/kriptoburak-hermes-tweet/kriptoburak/hermes-tweet --json
python3 scripts/validate.py --all
python3 scripts/security_scan.py --all
git diff --check
```

## What changed?
Refreshed the open submission from Hermes Tweet 0.1.0 to 0.1.6. The skill body now matches the current Hermes Tweet registry skill, including current Hermes Agent plugin enablement guidance, project-local trust notes, action-gating rules, and cron/unattended workflow safety guidance.
