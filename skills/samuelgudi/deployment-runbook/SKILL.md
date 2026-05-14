---
name: deployment-runbook
description: Use this skill when writing or improving a deployment runbook for a service, or when you need a structured deploy procedure that someone else — or a future you — can follow under pressure. Covers runbook structure, pre-flight checks, deploy steps, verification, and rollback.
---

# deployment-runbook

A deployment runbook is a procedure someone can follow to ship a service safely **without already knowing how it works**. The test of a good runbook: hand it to a person who has never deployed this service, and they succeed — or fail safely and recover — without asking anyone.

Deploys go wrong precisely when the conditions are worst: late, under pressure, done by whoever is available. A runbook is the artifact that makes the procedure independent of who is running it and how stressed they are.

## Use this skill when

- A service is deployed by hand, or by a procedure that lives only in one person's head.
- An existing runbook exists but people still have to ask questions to use it.
- You are setting up a new service and want the deploy procedure written down before the first 2am incident.

## Structure

A runbook has six sections, in this order:

1. **Prerequisites** — what must be true *before* you start: access and credentials needed, tools that must be installed, the branch/artifact/version being deployed. If a prerequisite is missing, the operator finds out here, not three steps in.
2. **Pre-flight checks** — quick checks that this is a safe moment to deploy: is the target healthy now, is there a freeze in effect, is the change actually the one intended. Each check has a clear pass/fail.
3. **Deploy steps** — the numbered procedure. See the rule below.
4. **Verification** — how to *know* the deploy worked. Objective, not "looks fine".
5. **Rollback** — how to undo it. See the rule below.
6. **Post-deploy** — anything to do after success: announce, close the ticket, re-enable something that was paused, watch a dashboard for N minutes.

## The rule for deploy steps

Every step is **three things**: the exact command, the expected result, and what to do if it does not happen.

```markdown
3. Apply the database migration:
   `./manage.py migrate`
   Expected: ends with "Applying <name>... OK", exit code 0.
   If it fails: do NOT proceed to step 4. The schema is now partially
   applied — go to Rollback step R2 before retrying.
```

A step that is only a command ("run migrate") assumes the operator knows what success looks like and what failure means. Under pressure, they do not. Spell it out.

Steps must be **copy-pasteable and context-free**. No `cd into the right directory` — say which directory. No `the usual flags` — write the flags.

## The rule for verification

Verification must be **objective** — a command, a status code, a specific log line, a health endpoint returning `200`. "Check that the site looks okay" is not verification; it is hope. The operator should be able to answer "did it work?" with yes or no, not with a feeling.

If the only way to verify is to look at something, say *exactly* what to look at and what the right and wrong versions look like.

## The rule for rollback

- **Rollback must be real, not aspirational.** "Restore from backup" is not a rollback procedure unless the restore has actually been performed and timed. If you have never rolled this service back, you do not have a rollback section — you have a guess.
- **Rollback steps follow the same three-part rule** as deploy steps: command, expected result, failure handling.
- **Every deploy step that can leave the system in a partial state must point at the rollback step that recovers it.** The migration example above does this. Partial states are where deploys turn into incidents.
- State the **point of no return** explicitly, if there is one — the step after which rollback is no longer clean and a forward-fix is the only option.

## Anti-patterns

- **"It should just work."** If it always just worked, there would be no need for a runbook. Write down what failure looks like.
- **No rollback section, or an untested one.** The rollback is the half of the runbook you reach for when things have already gone wrong. It is the half that must be most trustworthy.
- **Verification by vibes.** "Looks fine" is not a check. Give a command or a concrete observable.
- **Steps that assume context.** "Deploy as usual", "the normal way" — these work only for the person who already knows. That person is not the audience.
- **A runbook that has drifted from reality.** A runbook describing last quarter's procedure is worse than none — it is confidently wrong. Update it in the same change that changes the deploy.
- **Burying the freeze/safety checks at the end.** Pre-flight checks go *before* the deploy steps, because their job is to stop a deploy that should not happen.

## What this skill does not do

- It does not design a CI/CD pipeline or automate the deploy — it documents a procedure, whether that procedure is manual or a sequence of pipeline triggers.
- It does not cover infrastructure provisioning — it assumes the target environment exists.
- It does not decide deployment *strategy* (blue-green, canary, rolling) — it documents whatever strategy you have chosen so someone else can execute it.
