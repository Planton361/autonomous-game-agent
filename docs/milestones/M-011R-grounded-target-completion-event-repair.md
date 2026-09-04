---
id: M-011R
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m011r-grounded-target-completion-event
canonical_phase: D
legacy_working_label: null
---

# M-011R — Grounded Target Completion-Event Repair

## Outcome

Repair the Manager event boundary so an existing grounded target round-trips through a terminal `TaskCompletionEvent` and SQLite persistence.

Parent blocker: M-011.

Reason: `TaskSpec.target` is an existing typed `GroundedTarget`, while the completion event previously accepted only a scalar-value JSON object and therefore rejected nested target evidence and screen-position fields.

## Scope

- Preserve the existing `GroundedTarget` contract in `TaskCompletionEvent`.
- Preserve that exact target when converting a scheduler completion to an event.
- Serialize the typed target explicitly for the existing SQLite `target_json` column.
- Cover both grounded target variants, targetless events, terminal verifier completion, JSON round-trips, and SQLite round-trips.

## Out of Scope

- M-011 hierarchical execution composition or any other capability work.
- TaskSpec, target schema, SQLite schema, Manager lifecycle, verifier, reward, bridge, transport, game, or dependency changes.

## Acceptance Criteria

- `VisibleObjectTarget` and `VisibleScreenPointTarget` remain typed after event JSON and SQLite round-trips.
- A verifier-terminal completion with a grounded target converts into a successful completion event.
- Targetless completion events retain `target=None`.
- The scalar-only `JsonObject` contract remains unchanged.
- `target_json TEXT` remains the persistence schema.

## Verification

Run focused baseline and blocker reproduction before production edits; run focused final, target-contract search, full pytest, Ruff, diff, and CLI-help validation; obtain read-only review.

## Git Handoff

Use `codex/m011r-grounded-target-completion-event`; explicitly stage intended files, commit, push, create a Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this repair needs TaskSpec or target-schema changes, a SQLite migration, Manager lifecycle or verifier/reward changes, widening generic `JsonObject`, a dependency, or canonical revision.
