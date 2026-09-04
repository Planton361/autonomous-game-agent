---
id: M-012
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m012-verified-outcome-replan-context
canonical_phase: D
legacy_working_label: null
---

# M-012 — Verified Outcome Replan Context

## Outcome

Create a pure Manager-side mapping from a terminal verifier-backed `TaskCompletionEvent` and caller-owned base memory summary to a new memory summary with one evidence-backed `recent_skill_outcome` for a subsequent Cortex call.

## Scope

- Add a small pure replan-context helper and narrow error type.
- Admit only terminal independent verifier outcomes with verifier evidence.
- Preserve caller context and append one deterministic, game-agnostic outcome note.
- Prove compatibility with the existing Cortex evidence-scope boundary.

## Out of Scope

- Replan loops, Cortex calls in production, task submission/execution, ManagerStop reinterpretation, persistent memory, transport, live activity, and M-013.

## Acceptance Criteria

- SUCCESS and FAILURE verifier results produce one `observed_fact` outcome using exact verifier evidence.
- ManagerStop-only, nonterminal, and evidence-free verifier outcomes fail closed.
- Existing context and prior outcome entries remain unmodified and retained.
- Cortex accepts prior verifier evidence from the resulting outcome context while fabricated evidence remains rejected.

## Verification

Run focused baseline/final tests, dependency checks, full pytest, Ruff, diff, CLI-help validation, and read-only review.

## Git Handoff

Use `codex/m012-verified-outcome-replan-context`; explicitly stage intended files, commit, push, create a complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs a TaskCompletionEvent, Cortex/context/planner schema, persistent-memory, loop, dependency, or canonical change.
