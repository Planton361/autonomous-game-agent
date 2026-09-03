---
id: M-009
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m009-grounded-cortex-task-submission
canonical_phase: D
legacy_working_label: null
---

# M-009 — Grounded Cortex Task Submission

## Outcome

Compose canonical Observation, evidence-bounded planner output, current-evidence grounding, and Manager validation into one pending-task submission path.

## Scope

- Add one Manager-owned composition boundary using the existing planner protocol, M-008 request builder, GroundingService, and ManagerOrchestrator.
- Preserve targetless submission without a grounding-service call.
- Submit target-required results, including failures, through existing Manager validation.
- Add deterministic unit and bridge-assisted composition coverage.

## Out of Scope

- Task start or execution, Body/Input/Verifier use, replanning, target-selection logic, boundary/schema changes, live transport, live LLM, game launch, and real input.

## Acceptance Criteria

- Manager capabilities constrain the planner call and exact planner output is preserved.
- Targetless skills skip grounding and queue pending tasks.
- Target-required skills use the M-008 request and existing GroundingService exactly once.
- Failed and incompatible grounding results reach Manager revalidation without a queued task.
- Ambiguous candidates are rejected rather than guessed.
- No task starts or executes.

## Verification

Run focused baseline and final suites, source-dependency checks, full pytest, Ruff, diff, and CLI-help validation; obtain read-only review.

## Git Handoff

Use `codex/m009-grounded-cortex-task-submission`; explicitly stage intended files, commit, push, create a Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this requires changes to existing submission, grounding, Manager, schema, Observation, or planner boundaries; task execution, semantic target matching, live transport, dependencies, or canonical revision.
