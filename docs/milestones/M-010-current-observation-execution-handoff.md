---
id: M-010
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m010-current-observation-handoff
canonical_phase: D
legacy_working_label: null
---

# M-010 — Current Observation Execution Handoff

## Outcome

Preserve an already-consumed canonical planning observation as the first observation for later execution, then delegate later reads to the original online source.

## Scope

- Add a generic `PrimedObservationSource` ordering adapter in the Observation layer.
- Return the exact initial object once without consuming the remaining source.
- Delegate each later observation read exactly once.
- Add unit and deterministic bridge-to-SkillRunner coverage.

## Out of Scope

- Observation Protocol, Bridge, SkillRunner, TaskExecutor, Cortex, Manager, Body, Verifier, schema, transport, task execution composition, and live-runtime changes.

## Acceptance Criteria

- Construction and first observation perform no remaining-source pull.
- The initial Observation is returned exactly once by identity.
- Subsequent observations preserve source-owned order, exhaustion, and errors.
- The adapter has only generic Observation-layer dependencies.
- A planning bridge Observation is reused as the existing SkillRunner start Observation in a DryRun test.

## Verification

Run focused baseline and final suites, dependency checks, full pytest, Ruff, diff, and CLI-help validation; obtain read-only review.

## Git Handoff

Use `codex/m010-current-observation-handoff`; explicitly stage intended files, commit, push, create a Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this requires a Protocol, Bridge, SkillRunner, TaskExecutor, Cortex/Manager, schema, transport, dependency, or canonical change.
