---
id: M-005
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m005-manager-task-execution-slice
canonical_phase: D
legacy_working_label: null
---

# M-005 — Manager Task Execution Slice

## Outcome

Execute one already-running Manager task through its exact Manager-selected universal Body skill, an independently selected task-bound Verifier, the guarded `SkillRunner`, and the existing Manager completion path.

## Scope

- Add the small `ManagerTaskExecutor` composition boundary.
- Bind `TaskSpec.selected_skill` through `SkillCatalog.get` and preserve the exact grounded target.
- Bind the independent verifier through `VerifierCatalog.for_task`.
- Delegate execution to `SkillRunner` and closure to `ManagerOrchestrator.complete_from_skill_run`.
- Add deterministic unit and bridge-assisted DryRun integration coverage.

## Out of Scope

- Cortex or LLM planning, replanning, reward derivation, and direct primitive execution.
- Live bridge transport, game launch, live input, and any Observation or bridge contract change.
- Changes to SkillRunner, ManagerOrchestrator, catalogs, verifier implementations, or canonical sources.

## Acceptance Criteria

- A running task is required before skill selection or observation consumption.
- The Manager-selected skill and target are passed unchanged to `SkillCatalog.get`.
- Catalog binding mismatches fail before execution.
- The verifier comes only from `VerifierCatalog.for_task`.
- The executor delegates to existing `SkillRunner` and `ManagerOrchestrator` paths.
- Nonterminal results do not manufacture task completion.
- Manager-stop closure remains the existing orchestrator authority.
- A synchronized bridge-assisted DryRun slice reaches a verifier-backed `TaskCompletionEvent`.

## Verification

Run the focused M-005 suite, authority searches, then the repository standard pytest, Ruff, diff, and CLI-help checks.

## Git Handoff

Use `codex/m005-manager-task-execution-slice`; stage intended files explicitly, commit, push, create a Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if execution requires changing SkillRunner, ManagerOrchestrator, catalog contracts, bridge/Observation contracts, canonical sources, a new dependency, live transport, Cortex/LLM work, or automatic replanning; also stop on untrustworthy validation or three failed targeted fixes.
