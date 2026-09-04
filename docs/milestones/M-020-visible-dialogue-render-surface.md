---
id: M-020
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m020-visible-dialogue-surface
canonical_phase: D
legacy_working_label: null
---

# M-020 — Visible Dialogue Render-Surface Probe

## Outcome

Add a pure RPG Maker MV render-tree probe that reports only whether a visibly active
`Window_Message` makes the surface dialogue state observable.

## Scope

- Traverse only the supplied render/display tree.
- Require an open, rendered, visible message window and visible ancestors.
- Return only `ui_state: dialogue` or `ui_state: unknown`.
- Compose the result with the existing M-019 request-bound payload builder.

## Out of Scope

No game-model or message-queue access, text/sprite extraction, scene mutation, file I/O,
transport, polling, live activity, dependency changes, or M-021 work.

## Acceptance Criteria

- Missing engine types, malformed roots, hidden/closed windows, hidden ancestors, and absent
  message windows fail safely to `unknown`.
- A visibly active rendered `Window_Message` produces `dialogue`.
- The source has no hidden state, I/O, network, timer, or input access.
- The composed request-bound dialogue payload remains accepted by the existing Python sanitizer.

## Verification

Run focused bridge tests, full pytest, Ruff, format, diff, CLI-help, source-scope checks, and
independent review. Tests remain source/contract plus Python-sanitizer compatibility; no Node
tooling is added.

## Git Handoff

Use `codex/m020-visible-dialogue-surface`; explicitly stage intended files, commit, push, create a
complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs model-state reads, message/text internals, dependencies,
transport, polling, live execution, or existing Python Bridge contract changes.
