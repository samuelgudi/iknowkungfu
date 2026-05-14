---
name: lessons-learned-log
description: Use this skill when a mistake, a non-obvious fix, or a hard-won insight should be recorded so it is not rediscovered the hard way later. Covers what makes a lesson worth keeping, the one-line rule format, where lessons live, and when to read them back.
---

# lessons-learned-log

A lessons log is a growing list of short rules, each one distilled from a real mistake or a real discovery. Its purpose is narrow and specific: stop the same mistake from happening twice.

A lesson is **not** an incident report, a postmortem, or a journal entry. It is a single actionable rule. The report explains what happened; the lesson says what to do next time. This skill is about the second thing.

## Use this skill when

- A mistake was made that should not be repeated.
- A non-obvious solution was found to a problem that will recur.
- A pattern was noticed that future work in this area should account for.

If the thing you learned is obvious in hindsight to anyone, it is not a lesson — it is just knowledge. A lesson is something that *was not obvious* and cost something to discover.

## The format

One line per lesson:

```markdown
- [YYYY-MM-DD] When {situation}, {what to do or remember}. (why — what went wrong)
```

Three parts, all mandatory:

- **The date.** Context decays. A lesson from two years ago about a tool that has since changed needs to be re-evaluated, and the date is what tells you to re-evaluate it.
- **The rule.** A *situation* and a *response*. "When committing code, push immediately afterward" — not "be careful with git". A rule you cannot act on is not a rule.
- **The why.** What actually went wrong. The why is what makes the rule stick — and it is what lets a future reader judge whether the rule still applies, or whether the underlying cause is gone.

Examples:

```markdown
- [2026-04-01] When committing code, push immediately afterward. (lost two releases of work to disk failure because the commits were never pushed)
- [2026-03-28] When installing CUDA-build PyTorch with a package manager, install torch separately first with the explicit index URL, then the rest. (a combined install resolves every dependency against the CUDA index, which does not host the non-torch packages)
- [2026-04-04] When a templated UI silently ignores an event handler, bind it in code rather than inline in the template. (inline handlers fail silently in template-owner documents — no error, just nothing happens)
```

## Where lessons live

Lessons are only useful if they are read at the right moment, so organise them **by domain**, not by date — one file per area:

| File | Read before |
|---|---|
| `problem-solving.md` | Complex, multi-step, or unfamiliar tasks |
| `debugging.md` | Hunting a bug |
| `code-quality.md` | Writing or reviewing code |
| `architecture.md` | System design, starting something new |
| `security.md` | Auth, input handling, anything exposed |
| `performance.md` | Optimisation work |

Adapt the set to your actual domains — the principle is "grouped so the relevant ones surface together", not this exact list. Within a file, append new lessons; the file is a flat list under a title.

## Reading lessons back

Capturing lessons is half the skill. The other half is **reading the relevant file before starting work in that domain.** A lesson written and never re-read prevents nothing. Each rule is a landmine already stepped on — the few seconds it takes to scan the file is the entire return on having written it.

Make it a habit: about to debug something hard? Scan `debugging.md` first. About to design something? Scan `architecture.md`.

## Pruning

The log is curated, not append-only-forever. A rule that turns out to be wrong, or whose underlying cause no longer exists (the tool was fixed, the constraint was lifted), should be **deleted**. The date and the "why" are what let you make that call. A log full of stale rules is one nobody trusts enough to read.

## Anti-patterns

- **Multi-paragraph reports.** A lesson is one line. If it needs paragraphs, what you have is a postmortem — keep that elsewhere and distil the *rule* into the log.
- **No date.** Without it you cannot tell a current rule from a stale one.
- **No why.** A bare rule with no reason is brittle: it cannot be evaluated, it cannot be applied to edge cases, and it does not stick.
- **Rules too vague to act on.** "Be careful with migrations" is not a lesson. "When adding a NOT NULL column to a populated table, ship it in two migrations — add nullable, backfill, then enforce" is.
- **Write-only log.** Capturing lessons and never reading them back is effort with no payoff. The read habit is not optional.
- **Hoarding stale rules.** Delete what is wrong or obsolete. Trust in the log is the asset; stale entries spend it.

## What this skill does not do

- It does not replace incident reports or postmortems — those are a different, longer-form artifact. This is the one-line rule distilled *from* them.
- It does not prescribe a storage system — plain markdown files work; so does anything searchable. The format and the read-back habit are what matter.
- It does not capture lessons for you — noticing that something *was* a lesson is a judgement call made in the moment.
