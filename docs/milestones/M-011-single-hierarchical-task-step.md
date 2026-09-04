---
id: M-011
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m011-hierarchical-task-step-recut
canonical_phase: D
legacy_working_label: null
---

# M-011 — Single Hierarchical Task Step

M-011R prerequisite satisfied: this is a fresh recut after the completion-event grounded-target repair. The prior blocked M-011 draft worktree is not reused or modified.

## Outcome

Compose exactly one bounded attempt from an `ObservationSource` through evidence-bounded Cortex planning, current-evidence grounding, Manager scheduling/start, primed current-observation execution, guarded Body action, independent verification, and Manager task completion.

## Scope

- Add a composition-only `HierarchicalTaskStepRunner` and result record.
- Reuse `GroundedCortexTaskSubmitter`, `ManagerOrchestrator`, `PrimedObservationSource`, and `ManagerTaskExecutor` without duplicating their logic.
- Add deterministic unit and bridge-assisted DryRun integration coverage, including the repaired typed completion target path.

## Out of Scope

- Replanning, repeated autonomous execution, live transport/game/input, M-012, and modifications to existing planning, grounding, lifecycle, execution, bridge, observation, verifier, or target-event boundaries.

## Acceptance Criteria

- An idle scheduler is required before the single planning observation is read.
- The exact planning observation is primed as the first execution observation.
- Exactly one plan, submission, start, and execution attempt occurs.
- Terminal outcome closure remains owned by the existing verifier/ManagerStop and Manager paths.
- Nonterminal execution creates no completion or replan.
- A deterministic bridge-assisted path produces a typed target-preserving successful completion event with two payload pulls and DryRun-only input.

## Verification

Verify M-011R target-event regressions, focused baseline/final suites, source dependency constraints, full pytest, Ruff, diff, CLI help, and read-only review.

## Git Handoff

Use `codex/m011-hierarchical-task-step-recut`; explicitly stage intended files, commit, push, create a complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs any existing boundary change, lifecycle redesign, automatic replanning, live transport, dependency, or canonical revision.
