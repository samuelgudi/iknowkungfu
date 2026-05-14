---
name: session-handoff
description: Use this skill when an agent's working session is approaching its context limit or ending mid-task and the work must resume cleanly in a fresh session. Covers what state to capture, how to structure a handoff document, and how a handoff differs from a final wrap-up.
---

# session-handoff

A handoff is a document the *next* session reads to resume work without re-deriving everything from scratch. It is written for a reader with **zero prior context** — no memory of the conversation, no idea what was tried and rejected, no implicit knowledge of why the current state looks the way it does.

The failure mode this skill prevents: a session ends (context exhausted, or stopped mid-task), the next session opens, and the first twenty minutes are spent reconstructing what the previous session already knew.

## Use this skill when

- The session's context window is filling up and the task is not finished.
- A task is being stopped mid-flight and someone (or a future session) will pick it up later.
- Someone explicitly asks for a handoff, a "save state", or a "pick up where we left off" note.

## Handoff vs. wrap-up

These are different documents — do not conflate them.

| | Handoff | Wrap-up |
|---|---|---|
| Purpose | Resume *unfinished* work | Record *finished* work |
| Audience | The next working session | The project record / your future self |
| Trigger | Context pressure, mid-task stop | Task complete |
| Includes commits/pushes? | No — work is still in progress | Yes — that is the point |
| Lifespan | Discarded once the work resumes | Permanent |

If the work is done, you want a wrap-up (commit, changelog entry, close the issue). If the work is *not* done, you want a handoff. This skill is about the handoff.

## What to capture

A good handoff has exactly five things. More than this is noise; less than this forces re-derivation.

1. **State** — one or two sentences: what was being done, and how far along it is. The orientation line.
2. **Decisions** — every non-obvious choice made *and the reason for it*. Without the reason, the next session cannot tell a deliberate decision from an accident, and will "fix" things that were intentional.
3. **In-progress work** — what was mid-change when the session stopped, and the **exact resume point**: the file and line, the half-applied edit, the command that was about to run. "Continue the refactor" is not a resume point. "`src/auth/session.ts:80` — `validateToken` is extracted but its three callers still call the old inline version" is.
4. **Next steps** — the remaining work, ordered by priority, each one a concrete actionable instruction — not a topic.
5. **Critical context** — the things that, if the next session does not know them, will cause a wrong turn: a constraint discovered the hard way, a gotcha, a dead end already explored, an explicit instruction from the user that must be respected. Only things that change behaviour. If it would not change what the next session does, leave it out.

## Document structure

```markdown
# Session Handoff — {date} [{topic}]

## State
{1-2 sentences: what was being done and its current state}

## Decisions
- {decision}: {choice made} — why: {reason}

## In Progress
- {task} — exactly where it stopped: {file:line / half-done edit} — resume from: {concrete instruction}

## Next Steps
1. {highest priority — concrete, actionable}
2. {next — concrete, actionable}

## Critical Context
{Constraints, gotchas, dead ends already explored, user instructions to respect.
Only things that would change what the next session does.}
```

Keep it tight — aim for something that can be read in under two minutes. A handoff that is as long as the conversation it summarizes has saved no one any time.

## Anti-patterns

- **Vague resume points.** "Finish the API work" tells the next session nothing it did not already know. Name the file, the line, the exact next action.
- **Decisions without rationale.** A choice with no "why" reads as arbitrary, and arbitrary-looking choices get reverted. Always record the reason.
- **Dumping raw history.** The handoff is a *distillation*, not a transcript. The next session does not need every step that was tried — it needs the conclusions.
- **"Everything is critical."** If the Critical Context section lists ten things, none of them stand out. It should hold the two or three landmines, not a project overview.
- **Writing it too late.** A handoff written after the context window is already full is a handoff written from a degraded view of the session. Write it when you notice the pressure, not when you hit the wall.
- **Including commit/push instructions.** Those belong in a wrap-up. A handoff describes work that is *not yet* in a committable state.

## What this skill does not do

- It does not commit, push, or update any project record — that is a wrap-up's job.
- It does not decide *whether* to stop the session — it covers how to capture state once that decision is made.
- It does not define where handoff files live or how they are named — that is environment-specific. Pick a consistent location and a `{date}-{topic}` naming scheme and stay with it.
