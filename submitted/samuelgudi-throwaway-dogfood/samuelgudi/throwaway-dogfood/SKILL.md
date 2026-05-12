---
name: throwaway-dogfood
description: Use this throwaway skill to verify the agent-skills submit pipeline end-to-end during a dogfood walkthrough. Never merge this.
---

# Throwaway dogfood skill

This skill exists only to rehearse the `agent-skills submit` pipeline in a controlled way. The PR it produces is meant to be closed without merging.

## Why

We want to surface bugs in the validate -> sanitize -> security_scan -> review render -> git branch -> gh pr create flow before submitting a real skill.

## Behaviour

There is nothing to do. The body is here purely so SKILL.md is non-empty and survives validation.
