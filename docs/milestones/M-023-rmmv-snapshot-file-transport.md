---
id: M-023
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m023-rmmv-snapshot-file-transport
canonical_phase: D
legacy_working_label: null
---

# M-023 — RPG Maker One-Shot Snapshot File Transport

## Outcome

Add a separate, one-shot RPG Maker/NW.js file transport that reads one completed M-018 request,
uses the existing pure visible bridge to build an M-021 response, and atomically publishes it
without overwriting an existing response target.

## Scope

- Require newline-complete strict UTF-8 request JSON.
- Delegate visible payload construction only to `FHVisibleBridge.buildSnapshotResponse`.
- Fsync a same-directory exclusive temporary file and hard-link publish it without replacement.
- Leave the request unchanged and clean up the temporary artifact.

## Out of Scope

No pure bridge-core change, hidden game-state access, polling, watchers, networking, feed writing,
sanitization, runtime assembly, live-game activity, dependencies, or M-024 work.

## Acceptance Criteria

- Incomplete, malformed, invalid-mode, unavailable-runtime, or pre-existing-target cases fail closed.
- A visible message window can produce a correlated dialogue response through a Node harness.
- The response composes with M-021 correlation, M-022 relay, and M-014 JSONL readback.
- The transport has no direct game-model, input, or scene lookup authority.

## Verification

Run focused bridge/transport tests, source-scope checks, Node-backed behavioral tests when Node is
available, full pytest, Ruff, format, diff, CLI-help, and independent review.

## Git Handoff

Explicitly stage the declared files on `codex/m023-rmmv-snapshot-file-transport`, commit, push,
open a complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs pure bridge-core changes, hidden-state access, dependencies,
polling/watchers, transport expansion, or live runtime work.
