---
id: M-024
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m024-host-snapshot-capture-request
canonical_phase: D
legacy_working_label: null
---

# M-024 — Host Screenshot-to-Request Capture

## Outcome

Add one host-side composition that captures one visible frame, preserves durable screenshot evidence,
records its evidence event, and publishes an M-018 screenshot-bound bridge request.

## Scope

- Require matching run IDs before capture.
- Capture exactly one frame, save its screenshot evidence, and append metadata in one evidence event.
- Reuse the event-log screenshot lookup and existing M-018 request creation/publication boundaries.
- Return the exact evidence, event, request, and request-path records.

## Out of Scope

No capture/evidence/event boundary changes, response/relay/feed work, JavaScript, runtime assembly,
polling, networking, live-game activity, dependencies, or M-025 work.

## Acceptance Criteria

- No request can publish before durable screenshot evidence is logged.
- Existing request targets reject before capture where possible and remain race-safe through M-018.
- Failed publication preserves append-only screenshot evidence and its event.
- Sequential captures bind their requests to their own latest durable evidence IDs.

## Verification

Run focused capture/evidence/snapshot tests, source-scope checks, full pytest, Ruff, format, diff,
CLI-help, and independent review.

## Git Handoff

Explicitly stage intended files on `codex/m024-host-snapshot-capture-request`, commit, push, open a
complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs changes to existing capture, evidence, event-log, M-018,
response/relay/feed, runtime, dependency, or live-game boundaries.
