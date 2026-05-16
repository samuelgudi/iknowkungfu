---
name: persona-compression
description: Compress agent identity/persona files (system prompts, SOUL.md, CLAUDE.md, role definitions) using Proteus-style DSL. Covers identity statements, behavioral contracts, style rules, team rosters, handoff maps, and quality gates. Reduces 50-70% on behavioral sections while keeping operational instructions readable.
version: 1.0.0
author: Senna / Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [compression, token-optimization, dsl, proteus, persona, prompts, identity, system-prompts, behavioral-contracts]
---

# Persona Compression — Compressed DSL for Agent Identity Files

Apply Proteus-style compressed DSL to agent identity and persona files — system prompts, SOUL.md, CLAUDE.md, role definitions, behavioral contracts. Covers the unique structure of persona definitions: identity, style, behavioral rules, team rosters, handoff maps, decision authority, and quality gates. Operational instructions stay in readable prose.

When to use this vs `token-compression`: Use **persona-compression** when the file defines *who the agent is* (identity, style, behavior, team role). Use **token-compression** when the file defines *what the agent does* (skills, tasks, workflows). They complement each other — a system prompt might combine both.

## When to use

You have a persona file (system prompt, SOUL.md, CLAUDE.md, role config) that's growing long and you need to fit more behavioral signal into the first N tokens. Apply when:

- The identity/behavior section exceeds ~1,500 characters
- You have a team of agents and each persona loads into context simultaneously
- You want to encode complex routing logic or decision trees compactly
- You use compressed skill files (see `token-compression`) and want consistency across your prompt stack

**Don't use this for:** step-by-step instructions, code examples, setup/config, or anything a human audits directly. Keep a prose version for human review; ship the compressed version as the production prompt.

## Six Techniques (Adapted for Persona Files)

| # | Technique | Prose → Compressed |
|---|---|---|
| 1 | **Token packing** | `I handle debugging, testing, and build issues` → `{Debug,Test,Build}` |
| 2 | **Semantic normalization** | `Don't pretend to know things you don't` → `NoPretendKnow` |
| 3 | **DSL encoding** | `Always respond in English unless user writes otherwise` → `Lang=EN{UnlessUserOtherwise}` |
| 4 | **Structural compression** | 8-line handoff table → `Design→Architect|Code→Coder|Review→Reviewer` |
| 5 | **State-machine loops** | Multi-phase workflow → `Assess{X,Y}→Gather{A,B}→Dispatch{C}` |
| 6 | **Arrow conditionals** | `If uncertain, say so and verify` → `Uncertain→SayCheck` |

### How Each Applies to Persona Files

| Section of Persona | Best Technique |
|---|---|
| Identity statement | Semantic normalization + DSL encoding |
| Communication style | DSL encoding + arrow conditionals |
| Behavioral rules / Avoid | Arrow conditionals + token packing |
| Team roster | Structural compression |
| Handoff / routing map | Structural compression + state-machine loops |
| Decision authority | DSL encoding + arrow conditionals |
| Quality gates | Token packing + arrow conditionals |
| Collaboration norms | Semantic normalization |

---

## Compressed Persona Header Block

For persona files, add this block right after the frontmatter:

```
IDENTITY: {Trait.Trait.Trait}. {Role}{Scope}. {CorePrinciple}. {KeyDistinction}.
PersRubric(NEO-PI-R,0-100): O2E:75 I:85 AI:60 ... | C:85 SE:80 Ord:80 ... | E:35 W:60 ... | A:75 Tr:70 ... | N:25 Anx:25 ...
STYLE: {Trait}. {CommunicationPattern}. {EvidenceStandard}. {HowHandlesPressure}.
AVOID: {AntiPattern1}. {AntiPattern2}. {AntiPattern3}. {AntiPattern4}.
DEFAULTS: Lang=EN. {DefaultRule1}. {DefaultRule2}. {FallbackBehavior}.
TEAM: {Role:Function,Role:Function,...}
ROUTE: {Trigger→Target}|{Trigger→Target}|...
HANDOFF: {Artifact}→{Recipient}.
DECISIONS: Decide{Scope,Scope,...}. Escalate{Condition,Condition,...}.
GATE: {Check1}? {Check2}? {Check3}? {Check4}?
```

### Section-by-Section Guide

**IDENTITY** — 3 key traits separated by dots, then `{Role}{Scope}` packed format. Core principle is the one-line rule. Key distinction is what makes this persona unique vs generic.

**PersRubric (Optional)** — NEO-PI-R 30 sub-facet personality encoding on 0-100 scale. Five domains separated by `|`: Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism. Each domain has its sub-facets in shorthand (O2E=Openness to Experience, I=Intellect, AI=Aesthetic Intellect, etc.). Omit sections at default (50) to save space.

**STYLE** — 2-3 packed traits, communication pattern, how they handle evidence/uncertainty, how they respond under pressure.

**AVOID** — 4+ anti-patterns, each a normalized primitive. These are the most critical section for preventing failure modes.

**DEFAULTS** — Fallback behaviors for ambiguous situations. Language default first, then operational defaults.

**TEAM** — Packed roster with roles and functions. `{Role:Function}` pairs separated by commas.

**ROUTE** — Inbound/outbound routing: what triggers this persona's activation and where output goes.

**HANDOFF** — Specific deliverables to specific recipients. `{Artifact}→{Recipient}` pairs.

**DECISIONS** — Decision authority split: what the persona decides autonomously vs what requires escalation.

**GATE** — Quality gates as questions. The persona must answer "yes" to all before marking work done.

---

## Real-World Results

| Metric | Prose persona (10-agent team) | Compressed DSL |
|---|---|---|
| Average characters per persona | 4,100 | 1,330 (-68%) |
| Average lines | 75 | 14 |
| Personality encoding | None | 30 sub-facet NEO-PI-R scores |
| Route/handoff logic | Absent or buried in tables | Explicit state machine |
| Team awareness | Implicit | Explicit TEAM + ROUTE sections |

Real team example (10 agents, each converted):

| Profile | Prose (chars) | Compressed (chars) | Reduction |
|---|---|---|---|
| Foreman | 4,634 | 1,448 | 69% |
| Architect | 4,181 | 1,331 | 69% |
| Coder | 4,330 | 1,381 | 69% |
| Reviewer | 3,956 | 1,341 | 67% |
| Debugger | 3,915 | 1,311 | 67% |
| Researcher | 3,984 | 1,335 | 67% |
| DevOps | 4,025 | 1,269 | 69% |
| Security | 4,216 | 1,294 | 70% |
| Data Analyst | 3,825 | 1,279 | 67% |
| Secretary | 3,973 | 1,283 | 68% |

**Average: 68% reduction with more behavioral signal.**

---

## What To Compress vs Keep Prose

| Compress these ✅ | Keep in prose ❌ |
|---|---|
| Identity statement | Step-by-step operating procedures |
| Style / tone rules | Configuration / setup instructions |
| Behavioral rules and avoidances | Code blocks and script examples |
| Team roster and role descriptions | API references and schemas |
| Handoff / routing maps | Anything a human audits directly |
| Decision authority boundaries | Version history and changelogs |
| Quality gates | Attribution and license text |

---

## Workflow

### Step 1: Read the source persona

Read the full file. Identify which sections are behavioral (identity, style, team) and which are operational (setup, config, attribution).

### Step 2: Write the compressed header

Map each behavioral section to the corresponding compressed field. Focus on:

- **IDENTITY** — what makes this persona unique. If it sounds like it could apply to any agent, rewrite it before compressing.
- **AVOID** — every failure mode this persona has exhibited or could exhibit. This is the most valuable section for preventing mistakes.
- **ROUTE** — clear trigger→target mapping for handoffs. If the persona hands off work, encode it explicitly.
- **GATE** — operational gates that catch real errors. "Did I stay composed?" is not a gate. "Did I verify the file exists?" is.

### Step 3: Compress the behavioral sections

Apply the 6 techniques to identity, style, team sections. Leave operational text in prose.

### Step 4: Verify

1. Read the compressed header. Can you reconstruct the original persona instructions?
2. If any meaning is lost or ambiguous → revert that section to prose
3. If the compressed version is unambiguous → it passes
4. Read the full file — any orphaned section headers? (Common when a `## Style` section gets compressed into the header but the old marker remains)

---

## Pitfalls

- **Don't over-compress Identity.** The identity line anchors the persona's personality — keep it human-parseable. Compress the sections below it aggressively.
- **Don't remove the Avoid section.** It's the most skipped and most valuable part of a persona file. Every behavioral mistake the agent has made should have an entry here.
- **Test on your model.** GPT-4 and Claude parse compressed DSL well; smaller open-source models may stumble. Verify before deploying.
- **Keep a prose master copy.** The compressed version is for production (where every token matters). Keep the prose version for human review, onboarding, and iteration.
- **Mix the DSL vocabulary.** `{a,b,c}` for sets, `→` for sequences, `=` for assignments, `:` for pairs. Don't force everything into one format.
- **Watch for orphaned section headers.** When replacing prose sections with compressed alternatives, old `## Section Name` markers may remain with no content. Always verify.
- **Quality gates must be operational, not emotional.** "Did I check the output?" is better than "Did I do my best?".
- **Handoff maps need both directions.** `Design←Foreman|DesignDoc→Coder` is clearer than just one direction.

## Verification Checklist

After compressing a persona file:

- [ ] Can you reconstruct the original identity from the compressed version?
- [ ] Are all red flags / anti-patterns preserved in AVOID?
- [ ] Are all handoff routes explicitly mapped?
- [ ] Are quality gates operational (not emotional)?
- [ ] Are default behaviors specified for ambiguous situations?
- [ ] No orphaned section headers from replaced prose sections?
- [ ] Code blocks and operational instructions still in full prose?

## Attribution

Adapted from the Hermes Agent SOUL.md compressed DSL encoding methodology and the `token-compression` skill. The Proteus compressed DSL technique originates from the Proteus mega-prompt (Stoltz, 2023). The NEO-PI-R personality encoding is adapted from the Revised NEO Personality Inventory (Costa & McCrae, 1992).

## Related Skills

- `token-compression` — compressed DSL for skill files (general-purpose, covers all file types)
- `hermes-soul-authoring` — Hermes-specific SOUL.md authoring with compressed DSL section (if using Hermes Agent)
