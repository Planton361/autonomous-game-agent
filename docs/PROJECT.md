# Autonomous Game Agent — operational orientation

## Project

`Autonomous Game Agent`

## Purpose

Evidence-grounded hierarchical autonomous-agent research for long-horizon RPGs, with Fear & Hunger as the first pilot.

## Stable research sources

This page is operational orientation, not a replacement for the project charter. Stable research and architecture sources are:

- [`canonical/01_PROJECT_CHARTER.md`](canonical/01_PROJECT_CHARTER.md)
- [`canonical/02_ARCHITECTURE_CANONICAL.md`](canonical/02_ARCHITECTURE_CANONICAL.md)
- [`canonical/04_RESEARCH_PROTOCOL_CANONICAL.md`](canonical/04_RESEARCH_PROTOCOL_CANONICAL.md)

## Core non-negotiables

- Cortex never controls primitive keys directly; the Manager is the language/action authority.
- Body uses universal skills only, while an independent Verifier determines visible outcomes.
- Game-specific truth requires admissible evidence; hidden state and spoilers are not official authority.
- Body weights remain frozen within a run.

## Repository orientation

The implementation is organized around `src/fh_agent/perception`, `observation`, `bridge`, `planner`, `manager`, `body`, `game`, `verifier`, `memory`, `evals`, and `rl`.

## Authority matrix

| Claim | Authority |
| --- | --- |
| What is actually implemented? | GitHub HEAD + executable verification |
| What should be implemented now? | Active milestone contract |
| What are long-term research / architecture rules? | `docs/canonical/**` |
| What is operational project progress? | `docs/ROADMAP.md` |
| What was last actually checked? | Latest Session Report |
| What is product / research intent? | Explicit user decision |
