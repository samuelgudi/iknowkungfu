---
name: keep-a-changelog
description: Use this skill when creating or maintaining a project CHANGELOG, deciding what belongs in it, or preparing release notes. Covers the Keep a Changelog format, the six change categories, the Unreleased-section discipline, and how the changelog relates to semver.
---

# keep-a-changelog

A changelog is a curated, human-readable list of notable changes per release. It is **not** a git log. The git log is a complete, machine-generated record of every commit; a changelog is a deliberate, edited summary of what a *user of the project* needs to know. Conflating the two produces a changelog nobody reads.

This skill follows the [Keep a Changelog](https://keepachangelog.com/) convention.

## Use this skill when

- A project has no `CHANGELOG.md` and you are adding one.
- You are about to cut a release and need to turn the accumulated changes into release notes.
- You made a notable change and need to decide whether — and where — it goes in the changelog.

## Core principles

- **For humans, by humans.** Every entry is written for a person deciding whether to upgrade and what will change for them. "Bumped dependency X" matters only if it changes observable behaviour.
- **One section per version.** Reverse chronological — newest at the top.
- **An `[Unreleased]` section at the very top.** This is where entries land *as the work happens*. At release time it gets a version number and a date; a fresh empty `[Unreleased]` takes its place.
- **Dates in ISO 8601** (`YYYY-MM-DD`). Unambiguous across locales.
- **Notable, not exhaustive.** Internal refactors, formatting, test-only changes, and CI tweaks usually do not belong. If it does not change what a user can observe, leave it out.

## The six categories

Every entry goes under exactly one of these headings. They are fixed — do not invent new ones.

| Heading | For |
|---|---|
| `Added` | New features, new public surface. |
| `Changed` | Changes to existing behaviour. |
| `Deprecated` | Features still present but slated for removal — warn users now. |
| `Removed` | Features taken out in this release. |
| `Fixed` | Bug fixes. |
| `Security` | Fixes for vulnerabilities. Call these out so users know to upgrade urgently. |

Within a version, list only the categories that actually have entries. A release with just bug fixes has only a `Fixed` heading.

## Structure

```markdown
# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- New thing that is not yet in a release.

## [1.2.0] - 2026-05-14

### Added
- Description of a new feature, written for the person who will use it.

### Fixed
- Description of a bug, in terms of the wrong behaviour the user saw.

## [1.1.0] - 2026-04-30

### Changed
- ...
```

## The Unreleased discipline

The single habit that makes a changelog reliable: **add the entry when you make the change, not at release time.** Writing the whole changelog in one pass right before a release means reconstructing weeks of work from the git log under time pressure — exactly the situation that produces "misc fixes and improvements".

Releasing, then, is mechanical:

1. Rename `[Unreleased]` to `[<version>] - <date>`.
2. Add a fresh, empty `[Unreleased]` above it.
3. The version number is decided by the *content* of the section — see the relationship to semver below.

## Relationship to semver

The changelog and the version number describe the same release from two angles. The six categories map onto the bump:

- A `Removed` entry, or a `Changed` entry that breaks existing behaviour → **major** bump (or, in `0.x`, a minor bump).
- An `Added` entry, or a `Deprecated` entry → **minor** bump.
- Only `Fixed` (and non-breaking `Security`) entries → **patch** bump.

Deciding the bump is its own discipline — the changelog tells you *which categories changed*; a semver decision aid turns that into the number. See the companion skill `samuelgudi/semver-bump-decider`.

## Anti-patterns

- **Dumping the git log.** Commit messages are written for reviewers, in the language of the diff. Changelog entries are written for users, in the language of behaviour. They are not the same text.
- **Writing it all at release time.** Produces vague entries and missed changes. Use the `[Unreleased]` section continuously.
- **"Misc changes", "improvements", "various fixes".** These entries carry no information. If a change is notable enough to list, it is notable enough to describe.
- **No dates, or ambiguous dates.** `05/06/2026` is June in one country and May in another. Use `2026-05-06`.
- **Listing every internal change.** A changelog that includes every refactor and dependency bump buries the entries users actually need.
- **Skipping the format header.** The two-line note at the top tells readers (and tools) which conventions the file follows. Keep it.

## What this skill does not do

- It does not decide the version number — it organises the changes; `semver-bump-decider` turns them into a bump.
- It does not generate entries from commits automatically — the editorial judgement of *what is notable* and *how to phrase it for a user* is the whole point and cannot be automated away.
- It does not cover release tooling, tagging, or publishing — only the `CHANGELOG.md` content itself.
