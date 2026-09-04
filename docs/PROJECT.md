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
| What is actually implemented? | `main` HEAD + executable/CI verification |
| What should be implemented now? | Active GitHub Issue |
| What are long-term research / architecture rules? | `docs/canonical/**` |
| What defines capability order / phase exit gates? | `docs/canonical/03_RESEARCH_ROADMAP_CANONICAL.md` |
| What is the operational program? | GitHub Project |
| What is phase progress? | GitHub Milestone + Issues |
| What was last actually checked? | Pull Request and GitHub Actions records |
| What is product / research intent? | Explicit user decision |

## Delivery workflow

Routine work is planned as rolling-wave GitHub Issues under the Project and Phase A–N
Milestones. A Ready leaf Issue normally maps to one branch and one Draft Pull Request;
the user merges only after full GitHub CI and review. Issue closure drives Project Done.

M-025 is the final historical M-XXX micro-milestone. New work does not create routine
milestone files, session reports, or manual roadmap rows; the existing M-000R–M-025
records remain historical artifacts.
