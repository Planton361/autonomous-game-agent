---
id: M-025
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m025-rmmv-snapshot-request-watcher
canonical_phase: D
legacy_working_label: null
---

# M-025 — Bounded Snapshot Request Watcher

## Outcome

Add a finite event-driven RPG Maker/NW.js watcher that responds to newly atomically published
snapshot requests only by delegating to the existing M-023 one-shot transport.

## Scope

- Require an explicit positive finite `maxRequests` budget and an existing exchange directory.
- Use `fs.watch` only, filter strict safe request names, deduplicate attempts, and close at budget.
- Pass only `window.SceneManager._scene` unchanged to M-023.
- Expose idempotent manual closure.

## Out of Scope

No existing bridge/transport changes, direct response writing, polling, timers, hidden game-state
reads, feed/sanitizer work, input, network, live-game activity, dependencies, or M-026 work.

## Acceptance Criteria

- Matching filenames are attempted once at most; malformed matching requests still consume budget.
- Unsafe/unrelated paths are ignored without work.
- Existing response targets are left to M-023's no-overwrite authority.
- M-024 requests compose through the watcher, M-021, M-022, and M-014.

## Verification

Run focused bridge/capture/transport tests, source-scope checks, Node behavioral tests, full pytest,
Ruff, format, diff, CLI-help, and independent review.

## Git Handoff

Explicitly stage intended files on `codex/m025-rmmv-snapshot-request-watcher`, commit, push, open a
complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs hidden-state access, M-023 changes, polling/watch expansion,
dependencies, live input, or live runtime work.
