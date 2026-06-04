# REVIEW.md — theheavenlyd3mon/persona-compression@1.0.0

## What does it do?
Compresses agent identity/persona files (system prompts, SOUL.md, CLAUDE.md, role definitions) using a six-technique DSL adapted for persona structure — identity statements, behavioral contracts, style rules, team rosters, handoff maps, and quality gates. Operational instructions stay in prose.

## What does it access?

- Network endpoints: none
- Filesystem paths: none
- Environment variables: none
- Processes spawned: none

## Worst case if compromised?
Instructions only, no executable assets. No scripts, no network calls, no filesystem access. A compromised version could only alter the compression methodology described in prose — worst case is bad advice, not code execution.

## Why is this useful?
Complements `token-compression` (submitted separately). Where token-compression handles general skill/config file compression, persona-compression targets identity and behavioral files — system prompts, SOUL.md, CLAUDE.md, role definitions, behavioral contracts. No existing registry skill addresses persona-specific compression. Includes real-world data from a 10-agent team conversion (68% average reduction). Works across Claude Code, Hermes, Codex, OpenCode, Pi, and OpenClaw.

## Test evidence
(instructions-only skill — test evidence may be omitted)

## What changed?
(for updates only; leave blank for first-version)
