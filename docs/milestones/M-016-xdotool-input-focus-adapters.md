---
id: M-016
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m016-xdotool-input-focus-adapters
canonical_phase: D
legacy_working_label: null
---

# M-016 — Xdotool Input and Focus Adapters

## Outcome

Add concrete Linux/xdotool implementations of the existing `FocusGuard` and
`InputBackend` ports while preserving `InputExecutor` as the safety authority.

## Scope

- Send only caller-configured primitive key taps through argv-based xdotool commands.
- Treat `WAIT` as an OS-input no-op and fail closed for missing/failed mappings.
- Verify the active window's configured title and optional identity constraints exactly.
- Test subprocess behavior only through mocks.

## Out of Scope

No protocol or InputExecutor changes, real input, focus activation, emergency-stop redesign,
CLI or controlled-live-smoke changes, game-side work, network behavior, or M-017.

## Acceptance Criteria

- Input never uses a shell or activates a window.
- Focus failure, malformed output, timeout, and missing identity verification deny input.
- The real InputExecutor accepts a focused target and rejects a wrong target without sending a key.

## Verification

Run focused adapter/safety tests, full pytest, Ruff, diff, CLI-help, dependency checks, and
independent milestone review.

## Git Handoff

Use `codex/m016-xdotool-input-focus-adapters`; explicitly stage intended files, commit, push,
create a complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs InputExecutor/port changes, dependencies, emergency-stop
redesign, controlled-live-smoke work, live activity, or canonical changes.
