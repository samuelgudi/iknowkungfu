---
name: semver-bump-decider
description: Use this skill when deciding whether the next release of a SemVer-versioned library should bump major, minor, or patch. Walks through a checklist of change classes, surfaces the breaking-change risks people commonly miss, and explains 0.x and pre-1.0 conventions.
---

# semver-bump-decider

A decision aid for picking the next version number under [Semantic Versioning 2.0.0](https://semver.org/). The rule is short ("MAJOR for breaking, MINOR for additive, PATCH for fixes"); the application is where people slip.

## Use this skill when

- You have a list of changes (commits, PRs, a CHANGELOG draft) since the last release and need to choose the next version.
- A reviewer asks "is this a breaking change?" and you want a structured answer, not a gut feeling.
- You are maintaining a 0.x library and need to apply the relaxed pre-1.0 rules correctly.

## Decision rule

Apply in order. The first match wins.

1. **MAJOR** — any of:
   - A public symbol (function, class, type, exported field) was removed or renamed.
   - A public function's signature was changed in a non-additive way (required parameter added, parameter type narrowed, return type changed in a way callers can observe).
   - Default behaviour changed for an existing input (same call now returns different result, throws where it didn't, or has different side effects).
   - An advertised guarantee was weakened (e.g. a previously-stable order is no longer guaranteed, a previously-idempotent call is no longer idempotent).
   - The minimum supported runtime/language version was raised.
   - A previously-deprecated symbol was removed.
   - A configuration default flipped.
2. **MINOR** — none of the MAJOR conditions, and any of:
   - A new public symbol was added.
   - A new optional parameter was added with a back-compatible default.
   - A new field was added to a returned object (and consumers were not told to treat the object as closed).
   - A deprecation warning was added on an existing symbol (the symbol still works).
   - A new optional configuration knob was introduced with a back-compatible default.
3. **PATCH** — none of the above, only:
   - Bug fixes that restore documented behaviour.
   - Performance improvements that do not change observable behaviour.
   - Internal refactors, dependency bumps that don't surface in the public API, documentation, comment, or typo fixes.

If the change list mixes categories, the highest category wins.

## 0.x rule (pre-1.0)

Per SemVer §4: "Anything MAY change at any time" while major version is zero. In practice, most ecosystems treat `0.x` as:

- **0.MINOR bump** — breaking change.
- **0.MINOR.PATCH bump** — non-breaking change (additive or fix).

So in 0.x, breaking changes go in the MINOR position, not the (still-zero) MAJOR position. This is a convention, not a rule, but it is what npm, Cargo, pip-resolvers, and most release-tooling assume.

## Edge cases people get wrong

- **"It's only documented behaviour, not advertised behaviour."** If users could reasonably have built on it (e.g. iteration order of a set, error message format used by a downstream parser), changing it is a breaking change. Document the contract explicitly going forward, but bump MAJOR for this release.
- **Adding a new required field to an input type.** Even though it sounds additive, every existing caller breaks. MAJOR.
- **Tightening input validation.** Calls that previously succeeded now fail. MAJOR.
- **Bug fix that some users depended on.** If users were relying on the bug (a known footgun is "fixing" a permissive parser to be stricter), the fix is technically MAJOR. Pragmatic choice: announce as MINOR + clearly call out the change in the changelog and migration notes. Be honest about it.
- **Type-only change in a typed language.** If your public types are part of your contract (most TypeScript libraries: yes), narrowing or widening them is a breaking change. MAJOR.
- **Deprecation, then removal.** Deprecation alone is MINOR. The eventual removal is MAJOR — do not coalesce both into one MINOR.
- **Default value change.** Same call, different outcome — MAJOR, even if the user could "fix it" by passing the old default explicitly.
- **Adding a new module/file/entrypoint.** Additive: MINOR. Renaming or moving an existing entrypoint: MAJOR.
- **Internal types leaked to the public API.** If a previously-internal type starts appearing in a public return value, that is now part of your contract.

## How to apply

Given a list of changes:

1. For each change, classify it as MAJOR / MINOR / PATCH using the rules above.
2. Note any change you classified as MAJOR — call them out explicitly with the user, so the breaking-change decision is conscious.
3. Take the highest category across all changes. That is the bump.
4. For 0.x, translate per the 0.x rule above.
5. Write a one-line summary per category for the CHANGELOG: `Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security` (per [Keep a Changelog](https://keepachangelog.com/)).

## Anti-patterns

- **"It's a small change, just patch."** Size is irrelevant. A one-character rename of a public symbol is MAJOR.
- **"Nobody uses this, so it's not breaking."** If it is public, assume someone uses it. Either bump MAJOR or do not change it.
- **"The CHANGELOG already says it's breaking, so the version is fine."** No — the version IS the breaking-change signal for tooling and resolvers. The changelog is for humans.
- **"It's just a default — users can override."** Default changes are MAJOR. The user did not opt into the new behaviour.

## What this skill does not do

- It does not run on a diff for you — bring the change list and the API surface yourself.
- It does not handle non-SemVer schemes (CalVer, ZeroVer, ad-hoc). For those, the rules above are conceptual only.
- It does not decide whether a breaking change is *worth shipping* — only that, if you ship it, the bump is MAJOR.
