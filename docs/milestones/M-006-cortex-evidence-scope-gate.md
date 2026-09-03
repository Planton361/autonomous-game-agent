---
id: M-006
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m006-cortex-evidence-scope-gate
canonical_phase: D
legacy_working_label: null
---

# M-006 — Cortex Output Evidence Scope Gate

## Outcome

Accept a `PlannerOutput` only when every cited evidence ID occurs in the exact evidence-bearing `CortexContext` sent to that LLM call.

## Scope

- Add a small private evidence-scope check at the parsed `PlannerOutput` boundary in `Cortex.plan_next_goal`.
- Permit non-empty evidence IDs from the observation summary evidence list and retrieved facts, hypotheses, and recent outcomes.
- Reject the complete output when a claim or memory update cites any ID outside that context.
- Add deterministic `FakeLLMClient` coverage for accepted and rejected evidence paths.

## Out of Scope

- PlannerOutput or CortexContext schema changes, Manager composition, bridge dependencies, memory persistence changes, replanning, live LLM calls, game activity, and input.

## Acceptance Criteria

- Current and retrieved context evidence remains usable.
- Fabricated factual, hypothesis, memory-update, and mixed evidence is rejected with `PlannerOutputError`.
- `screenshot_id` without canonical `evidence_ids` grants no evidence authority.
- Existing hidden-state, direct-control, and skill-availability protections remain unchanged.
- Each valid or evidence-invalid response makes exactly one fake LLM request.

## Verification

Run the focused M-006 suites, Cortex dependency/scope searches, then full pytest, Ruff, diff, and CLI-help validation.

## Git Handoff

Use `codex/m006-cortex-evidence-scope-gate`; explicitly stage intended files, commit, push, create a Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this requires changing context/output schemas, Manager or bridge integration, persistent-memory behavior, a dependency, canonical sources, or trusted validation.
