# AGENTS.md — Stable coding-agent entry point

Start with [the canonical source index](docs/canonical/00_CANONICAL_SOURCE_INDEX.md).

## Authority and status

1. **GitHub HEAD** is authoritative for implementation status: what exists, is tested, was removed, or was renamed.
2. **`docs/canonical/`** is authoritative for the stable research vision, target architecture, research protocol, and capability sequence.
3. **The current working chat** carries temporary milestone, validation, blocker, and handoff state.

A roadmap statement is never evidence that a capability is implemented. Do not add current milestone, test-count, session-handoff, or commit-specific progress claims to stable repository documentation unless the user explicitly requests them.

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

## Coding workflow

Inspect relevant files before changing them. Keep changes small, typed, and testable; isolate side effects from pure logic. Do not silently alter architecture boundaries—request an architectural review when a requested change needs one. Do not add large dependencies without documenting the rationale.

For standard validation, run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```
