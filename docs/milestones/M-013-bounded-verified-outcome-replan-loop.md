---
id: M-013
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m013-bounded-replan-loop
canonical_phase: D
legacy_working_label: null
---

# M-013 — Bounded Verified-Outcome Replan Loop

## Outcome

Compose existing single-step execution and verified-outcome context into a finite Manager-side replan loop. Each next attempt may follow only a terminal, independently verifier-backed completion.

## Scope

- Add one pure composition runner with a caller-supplied finite step-ID budget.
- Reuse M-011 for each attempt and M-012 for outcome context.
- Stop on budget exhaustion, ManagerStop, or nonterminal execution.

## Out of Scope

- Persistent memory, production transport, live activity, restart/death handling, unbounded autonomy, and M-014.

## Acceptance Criteria

- No more attempts than supplied step IDs occur.
- SUCCESS and FAILURE verifier outcomes update ephemeral context for a subsequent attempt.
- ManagerStop and nonterminal outcomes stop without a further planning attempt.
- Each new attempt obtains a fresh observation through the existing M-011 runner.

## Verification

Run focused baseline/final tests, source dependency checks, full pytest, Ruff, diff, CLI-help validation, and read-only review.

## Git Handoff

Use `codex/m013-bounded-replan-loop`; explicitly stage intended files, commit, push, create a complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this requires changes to M-011, M-012, existing Manager/planner/observation boundaries, persistent memory, a loop redesign, dependencies, or canonical sources.
