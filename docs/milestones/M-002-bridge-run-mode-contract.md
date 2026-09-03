---
id: M-002
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m002-bridge-run-mode-contract
canonical_phase: D
legacy_working_label: null
---

# M-002 — Canonical Bridge Run-Mode Contract

## Outcome

The visible-state bridge accepts exactly `bridge-assisted` and `debug`; it rejects obsolete `official` and non-bridge modes without changing visible Observation semantics.

## Scope

- Define one bridge-specific `BridgeRunMode` at the Python sanitizer boundary.
- Use that type for sanitized payloads and receipts.
- Migrate bridge fixtures and add boundary regressions for accepted and rejected modes.
- Record Phase C completion and Phase D activation operationally.

## Non-goals

- bridge transport, live gameplay, bridge connection, or real input
- global run-mode normalization
- JavaScript policy duplication
- Cortex, Observation-schema, evaluator, or canonical-roadmap changes
- hidden-state bypass, contamination-state management, or M-003

## Acceptance Criteria

- `bridge-assisted` and `debug` are accepted; `official`, `screen-only`, `networked-api-exploratory`, `contaminated`, and `training` are rejected with `InvalidBridgePayloadError`.
- The receipt preserves the supplied canonical bridge mode and sanitized visible output strips `run_mode`.
- Forbidden and unknown fields remain denied identically in both bridge modes.
- Observation/evidence conversion remains unchanged.
- One bridge-specific mode type definition prevents sanitizer/receipt drift.

## Verification

Run focused bridge baseline and final suites, inspect obsolete-mode usage, then run pytest, Ruff, diff check, and CLI help. Inspect all changed paths and protected zero diffs.

## Git Handoff

Use the declared A2 branch, explicitly stage intended files, commit, push, Draft PR, and user merge only.

## Stop Conditions

Stop for absent M-001 merge, dirty workspace, required canonical/evals/global-run-mode/JS change, hidden-state weakening, Observation-schema change, live transport, dependency need, untrustworthy validation, or three failed focused fixes.
