# AGENTS.md — Stable coding-agent entry point

Start with [the canonical source index](docs/canonical/00_CANONICAL_SOURCE_INDEX.md).

## Claim-specific authority

Use the authority that matches the claim; there is no universal linear source hierarchy.

| Claim | Authority |
| --- | --- |
| Implementation truth | GitHub HEAD + executable verification |
| Current task | Active milestone |
| Long-term research / architecture | `docs/canonical/**` |
| Operational progress | `docs/ROADMAP.md` |
| Last actually executed checks | Latest session report |
| Product / research intent | Explicit user decision captured in milestone, ADR, or project sources |

A roadmap statement is never evidence that a capability is implemented. Current user intent is authoritative for intent; durable decisions must be written back to repository artifacts.

## Non-negotiable architecture and research rules

- Cortex is a slow, evidence-grounded planner. It may propose goals, hypotheses, universal capabilities, constraints, and success criteria; it must never directly control primitive keys, timings, or the `InputExecutor`.
- Manager is the sole authority that validates Cortex output, grounds visible evidence-linked targets, and opens, closes, suspends, or replans bounded skill contracts.
- Body acts only within an active Manager contract. It uses universal reusable skills, never game-specific room, enemy, quest, or ending shortcuts. Body weights are frozen for the duration of a run.
- Reflex is a fast Body path only: it may select contract-allowed actions for declared immediate visible conditions, and may not invent goals, expand permissions/budgets, suppress stop/replan signals, or bypass safety or logging.
- Verifier is independent of Cortex and determines visible success, failure, progress, and outcome evidence. A screenshot/hash change alone is not success.
- Learning and training occur between runs only: collect admissible experience with a frozen version, train a candidate, validate on held-out scenarios, certify or reject it, then activate only a certified version.
- Game-specific facts, grounded targets, outcomes, and memory updates require evidence IDs linked to admissible visible evidence.

## No-spoiler and run integrity

- Never use game guides, wikis, maps, spoilers, RPG Maker internals, event/map identifiers, switches, variables, databases, save-game internals, RAM-derived state, or other hidden state as an official authority.
- The optional bridge is deny-by-default and may expose only allowlisted information simultaneously visible to a player. Attempted forbidden access is an integrity incident.
- Preserve run-mode separation, network isolation where required, provenance, and contamination quarantine as defined by the canonical protocol.
- Log observations, proposed/executed/rejected actions, contracts, skill results, rewards, verifier outcomes, screenshots, and evidence links.

## Input safety

Never automate the wrong window. Primitive input requires an active valid contract, verified target-window focus, an allowed action, rate-limit capacity, a functional emergency stop, and durable logging with before/after evidence linkage. Do not launch the game or send input unless the user explicitly authorizes it.

## Milestone, Git, and session workflow

One Codex session normally completes one milestone. Read this file and the active milestone before changing files; use the claim-specific authority matrix above.

For a normal milestone:

```text
codex/<milestone>-<slug>
→ validate
→ stage intended files only
→ commit
→ push
→ Draft PR
→ User merge
```

Direct normal-milestone writes to `main` are forbidden after M-000R. Do not continue another milestone in the same Codex task. End with the current session-report format; old chats must not be required to resume the project.

`docs/canonical/**` may change only after an explicit user-authorized architecture/research review.

## Coding workflow

Inspect relevant files before changing them. Keep changes small, typed, and testable; isolate side effects from pure logic. Do not silently alter architecture boundaries—request an architectural review when a requested change needs one. Do not add large dependencies without documenting the rationale.

For standard validation, run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```
