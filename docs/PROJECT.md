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

The accepted active `ALIGN-2026-09-19-v1.0` control release records the replacement
Mission Run/Life Episode semantics and simplified project workflow:
[`orchestration/releases/ALIGN-2026-09-19-v1.0/README.md`](orchestration/releases/ALIGN-2026-09-19-v1.0/README.md).

## Core non-negotiables

- Cortex never controls primitive keys directly; the Manager is the language/action authority.
- Body uses universal skills only, while an independent Verifier determines visible outcomes.
- Game-specific truth requires admissible evidence; hidden state and spoilers are not official authority.
- Body weights remain frozen within a Mission Run; death/restart creates a Life
  Episode and does not replace the controller.

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

### Cross-device handoff

GitHub is the handoff authority between workstations. `origin/main` is the latest
accepted stable state, and one shared remote Issue branch (normally
`codex/<issue>-<slug>`) is the only active writer state for an Issue. Before
switching devices, the active workstation must have a clean working tree and its
local Issue-branch `HEAD` must equal the corresponding pushed remote branch
`HEAD`. A checkpoint commit is allowed for handoff, but it is not completion or
review evidence.

The receiving workstation must fetch with prune, check out the same Issue branch,
and fast-forward only from the remote before continuing. It must stop on local
dirt, divergence, an unexpected origin or tracking branch, or unresolved
conflicts. Direct work on `main`, automatic commit/push/merge, and synchronization
of generated caches, virtual environments, model caches, or machine-local
settings are not part of this workflow.

`uv run projectctl doctor` checks this state without fetching, pulling, committing,
pushing, installing tools, logging in, or changing authentication. Its optional
`--json` output is intended for later read-only workflow automation. A missing
`gh` or Codex CLI is reported as a warning; missing or stale local remote refs are
reported as unknown and never trigger an implicit network operation.

M-025 is the final historical M-XXX micro-milestone. New work does not create routine
milestone files, session reports, or manual roadmap rows; the existing M-000R–M-025
records remain historical artifacts.
