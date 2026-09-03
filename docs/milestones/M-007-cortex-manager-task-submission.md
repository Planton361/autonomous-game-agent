---
id: M-007
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m007-cortex-manager-task-submission
canonical_phase: D
legacy_working_label: null
---

# M-007 — Cortex → Manager Task Submission

## Outcome

Turn one canonical observation and caller-supplied memory summary into an evidence-bounded `PlannerOutput`, then submit that exact output through the existing Manager validation and scheduling boundary as a pending task.

## Scope

- Add a small `CortexTaskSubmitter` composition boundary with a structural planner protocol.
- Propagate the Manager runtime capability set to the planner call.
- Pass the exact planner output, caller-supplied grounding result, task ID, and planner provenance to `ManagerOrchestrator.submit_planner_output`.
- Cover targetless submission, Manager revalidation, grounding pass-through, M-006 provenance rejection, and deterministic bridge-assisted composition.

## Out of Scope

- Task start or execution, automatic grounding, replanning, verifier or reward work, Cortex/Manager boundary changes, live transport, networked LLM calls, game activity, and input.

## Acceptance Criteria

- Manager capability subset controls the planner call.
- Exact observation, memory summary, planner output, IDs, and supplied grounding result are forwarded.
- Targetless tasks queue as `PENDING`; no task starts automatically.
- Manager independently rejects unavailable skills and missing/failed grounding.
- M-006 evidence and direct-control rejections occur before Manager submission.
- The production glue has no bridge, memory retrieval, grounding-service, or execution dependency.

## Verification

Run focused M-007 tests, source-level authority searches, then full pytest, Ruff, diff, and CLI-help validation.

## Git Handoff

Use `codex/m007-cortex-manager-task-submission`; explicitly stage intended files, commit, push, create a Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if implementation requires changing Cortex, existing Manager boundaries, GroundingService, bridge/Observation contracts, persistent retrieval, execution, dependencies, or canonical sources.
