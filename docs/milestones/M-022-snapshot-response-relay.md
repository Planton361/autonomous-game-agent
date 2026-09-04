---
id: M-022
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m022-snapshot-response-relay
canonical_phase: D
legacy_working_label: null
---

# M-022 — Local Snapshot Response Relay

## Outcome

Add a one-shot host-side transport boundary that relays one complete, correlated M-021 response
payload unchanged into the existing append-only M-014 JSONL bridge feed.

## Scope

- Read only the supplied response path and require a newline-terminated complete JSON document.
- Validate the M-021 envelope and reuse its existing correlation helper.
- Serialize the unchanged raw payload as one UTF-8 JSONL record, append it, and fsync before success.
- Return immutable relay audit metadata.

## Out of Scope

No payload sanitization, screenshot-evidence inspection, Observation construction, feed reading,
polling, file transport discovery, live activity, dependency changes, or M-023 work.

## Acceptance Criteria

- Missing, incomplete, invalid, or mismatched responses leave an existing feed unchanged.
- Existing feed content is preserved; a valid relay contributes exactly one readable JSONL object.
- Unknown and forbidden raw fields reach the existing sanitizer unchanged.
- The response file is never mutated and parent directories are never created implicitly.

## Verification

Run focused snapshot/JSONL/bridge tests, full pytest, Ruff, format, diff, CLI-help, source-scope
checks, and independent review.

## Git Handoff

Use `codex/m022-snapshot-response-relay`; explicitly stage intended files, commit, push, create a
complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs M-014/M-021 changes, sanitizer use at the relay, polling,
dependencies, game-side transport, or live runtime work.
