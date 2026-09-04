---
id: M-018
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m018-bridge-snapshot-request
canonical_phase: D
legacy_working_label: null
---

# M-018 — Screenshot-Bound Bridge Snapshot Request

## Outcome

Create a host-side request contract that binds a future bridge-visible-state snapshot to one
already durable screenshot evidence ID.

## Scope

- Validate fixed bridge-assisted request metadata against the existing latest-screenshot lookup.
- Atomically publish deterministic request JSON without overwriting an existing target.
- Verify the request/event-log boundary remains read-only with respect to screenshot evidence.

## Out of Scope

No game-side producer, payload/feed writing, polling, screenshot evidence production, sanitizer,
bridge runtime, Manager/Game/CLI changes, live activity, or M-019 work.

## Acceptance Criteria

- Only the latest durable screenshot evidence for the request run is accepted.
- Missing, stale, wrong-run, blank, and wrong-mode requests fail closed.
- Publication has no partial target on failure and never overwrites an existing target.

## Verification

Run focused bridge/evidence tests, full pytest, Ruff, formatting, diff, CLI-help, source-scope
checks, and independent review.

## Git Handoff

Use `codex/m018-bridge-snapshot-request`; explicitly stage intended files, commit, push, create a
complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs screenshot-evidence, sanitizer, producer, live-smoke,
dependency, or canonical changes.
