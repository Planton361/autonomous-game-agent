# AGENTS.md — Stable coding-agent entry point

The frozen canonical research-source set is indexed at
[`docs/canonical/00_CANONICAL_SOURCE_INDEX.md`](docs/canonical/00_CANONICAL_SOURCE_INDEX.md).
Use the claim-specific authority rules below to decide which source governs a particular question.

## Claim-specific authority

Use the authority that matches the claim; there is no universal linear source hierarchy.

| Claim | Authority |
| --- | --- |
| Implementation truth | `main` HEAD + executable/CI verification |
| Current task | Active GitHub Issue |
| Long-term research / architecture | `docs/canonical/**` |
| Capability order / phase exit gates | `docs/canonical/03_RESEARCH_ROADMAP_CANONICAL.md` |
| Operational program | GitHub Project |
| Phase progress | GitHub Milestone + Issues |
| Last actually executed checks | Pull Request and GitHub Actions records |
| Product / research intent | Explicit user decision captured in an Issue, ADR, or project source |

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

## GitHub-native delivery workflow

Read this file and the active GitHub Issue before changing files; use the claim-specific authority matrix above. One leaf Issue normally maps to one Pull Request, and the default work-in-progress limit is one Issue.

For normal future work:

```text
GitHub Ready Issue
→ codex/<issue-number>-<slug>
→ focused local tests + static checks
→ stage intended files only
→ commit
→ push
→ Draft PR with `Closes #<issue-number>`
→ GitHub full CI
→ review
→ User merge
```

Do not write normal work directly to `main`, merge a Pull Request, or declare an Issue `done` merely because a Draft PR exists. Before merge, report only `ready for review`, `partial`, or `blocked`. Issue closure drives Project Done; phase closure requires the canonical exit gate, not closed implementation Issues.

M-025 is the final historical global M-XXX micro-milestone. Do not create routine `docs/milestones/M-XXX-*.md` files, per-PR session reports, or manual `docs/ROADMAP.md` milestone rows. Historical M-000R–M-025 artifacts remain unchanged.

`docs/canonical/**` may change only after an explicit user-authorized architecture/research review.

## Coding workflow

Inspect relevant files before changing them. Keep changes small, typed, and testable; isolate side effects from pure logic. Do not silently alter architecture boundaries—request an architectural review when a requested change needs one. Do not add large dependencies without documenting the rationale.

Use focused local validation during ordinary Issue work. GitHub Actions owns the full standard suite. Run the full local suite only for a high-risk boundary, CI unavailability, global repair, CI-workflow change, phase exit, or explicit user request.

For those full-local cases, run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```
