---
id: M-021
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m021-bridge-snapshot-response
canonical_phase: D
legacy_working_label: null
---

# M-021 — Request-Bound Bridge Snapshot Response

## Outcome

Add a pure response envelope that correlates one M-018 snapshot request with one M-019/M-020 raw
visible bridge payload without altering payload contents or sanitizer authority.

## Scope

- Validate non-blank response identifiers and exact request/run/payload provenance equality.
- Return the exact raw payload only after correlation passes.
- Add a JavaScript response builder that reuses M-020 scene payload composition.
- Verify forbidden and unknown payload fields remain available to the existing downstream sanitizer.

## Out of Scope

No raw-payload sanitization, schema changes, screenshot-evidence changes, file transport, polling,
live activity, hidden-state access, dependency changes, or M-022 work.

## Acceptance Criteria

- Missing or mismatched request, run, mode, and screenshot provenance fails closed.
- The response envelope is frozen and extra fields are forbidden.
- Payload contents are returned unchanged; the existing sanitizer still rejects prohibited fields.
- The JavaScript builder contains no new game-state extraction or runtime behavior.

## Verification

Run focused bridge tests, full pytest, Ruff, format, diff, CLI-help, source-scope checks, and
independent review. JavaScript coverage remains source/contract based; no Node dependency is added.

## Git Handoff

Use `codex/m021-bridge-snapshot-response`; explicitly stage intended files, commit, push, create a
complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs raw-payload/sanitizer/evidence changes, transport, polling,
hidden-state access, dependencies, or live execution.
