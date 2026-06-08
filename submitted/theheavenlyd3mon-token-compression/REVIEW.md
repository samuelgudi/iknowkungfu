# REVIEW.md — theheavenlyd3mon/token-compression@1.0.0

## What does it do?
Teaches a six-technique compressed DSL for shrinking behavioral/header sections of skill files and agent prompts (token packing, semantic normalization, DSL encoding, structural compression, state-machine loops, arrow conditionals). Operational instructions stay in readable prose.

## What does it access?

- Network endpoints: none
- Filesystem paths: none
- Environment variables: none
- Processes spawned: none

## Worst case if compromised?
Instructions only, no executable assets. No scripts, no network calls, no filesystem access. A compromised version could only alter the compression methodology described in prose — worst case is bad advice, not code execution.

## Why is this useful?
No existing registry skill addresses token optimization. Skills load verbatim into context, and behavioral sections (identity, style, when-to-use, red flags) are pure prose that compresses well. This skill teaches a repeatable DSL that reduces those sections 40–70% while keeping step-by-step instructions readable. Works across Claude Code, Hermes, Codex, OpenCode, Pi, and OpenClaw — agent-agnostic methodology, not platform-specific tooling.

## Test evidence
(instructions-only skill — no scripts, no executable assets. Test evidence not applicable.)

## What changed?
First version — no prior changes.
