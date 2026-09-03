---
id: M-008
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m008-grounding-request-derivation
canonical_phase: D
legacy_working_label: null
---

# M-008 — Grounding Request Derivation

## Outcome

Derive an auditable `GroundingRequest | None` from validated planner intent and the current canonical observation, without grounding or task submission.

## Scope

- Add a pure request builder using only `PlannerOutput`, `Observation`, target requirements, and `GroundingRequest`.
- Return `None` for targetless skills.
- Build target-required requests with exact selected skill, exact semantic goal, and ordered current-observation evidence only.
- Add builder and existing GroundingService compatibility coverage.

## Out of Scope

- GroundingService invocation in production, target selection, task submission/start/execution, Cortex integration, semantic matching, live transport, and schema changes.

## Acceptance Criteria

- Targetless skills return `None`.
- Target-required skills preserve selected skill and goal.
- Scope contains only non-empty, deduplicated current observation evidence in first-seen order.
- Historical planner evidence, descriptive screenshot ID, and sprite candidate evidence do not enter request scope.
- Empty scope remains a GroundingService-owned `insufficient_evidence` outcome.

## Verification

Run focused M-008 tests, dependency checks, then full pytest, Ruff, diff, and CLI-help validation.

## Git Handoff

Use `codex/m008-grounding-request-derivation`; explicitly stage intended files, commit, push, create a Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs a schema or existing-boundary change, automatic grounding/submission, semantic target matching, dependencies, or canonical revision.
