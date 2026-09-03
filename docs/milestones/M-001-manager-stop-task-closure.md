---
id: M-001
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m001-manager-stop-task-closure
canonical_phase: C
legacy_working_label: C7
---

# M-001 — Manager stop task closure

## Outcome

`ManagerStopResult` propagates through `TaskScheduler` / `TaskCompletion` to `TaskCompletionEvent`, without pretending that it is a `VerifierResult`.

## Why

The retrofit baseline has a distinct Manager/runtime control-plane stop that is not yet represented in task completion.

## In scope

- `TaskCompletion` gains separate ManagerStop provenance.
- The scheduler receives a typed manager-stop completion path.
- Timeout maps to existing `TIMED_OUT`; other canonical ManagerStop failure kinds close via existing `FAILED`, without a new lifecycle status.
- Exact `failure_kind`, reason, evidence, and manager-stop event ID remain available.
- The Orchestrator uses `ManagerStopResult` when present.
- Existing verifier-driven closure remains unchanged.

## Out of scope

- M-000R workflow changes
- rewards from `ManagerStopResult`
- fake verifier events or results
- making previous nonterminal verifier history closure authority
- unrelated manager, scheduler, or lifecycle refactors

## Acceptance criteria

Manager-stop closure is typed and provenance-preserving, verifier closure behavior remains intact, timeout and failure mappings use existing statuses, and targeted plus standard validation passes.

## Relevant sources / paths

`src/fh_agent/manager/`, `src/fh_agent/verifier/`, relevant task/scheduler tests, and `docs/canonical/02_ARCHITECTURE_CANONICAL.md`.

## Technical constraints

Manager and Verifier remain independent; no reward bypasses verified outcomes; no direct input or live runtime work.

## Verification

Add focused behavior tests first, then run the repository standard validation and inspect the final diff.

## Git handoff

Use the declared A2 branch, explicit staging, push, Draft PR, and user merge only.

## Stop conditions

Stop for architecture ambiguity, a need for canonical revision, non-local product scope expansion, blocked validation, or three failed targeted hypotheses.
