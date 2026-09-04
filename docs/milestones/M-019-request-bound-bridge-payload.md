---
id: M-019
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m019-request-bound-bridge-payload
canonical_phase: D
legacy_working_label: null
---

# M-019 — Request-Bound Bridge Payload Builder

## Outcome

Add a pure RPG Maker MV bridge builder that binds raw visible payload provenance to a validated
M-018 snapshot request while preserving the existing Python sanitizer boundary.

## Scope

- Validate fixed bridge-assisted request metadata and explicit visible-surface fields.
- Make the request screenshot ID authoritative and reject surface metadata overrides.
- Reject unknown and forbidden surface fields without sanitizing or interpreting them.
- Verify the JavaScript source contract and its compatibility with the existing Python sanitizer.

## Out of Scope

No filesystem transport, polling, live game integration, automatic scene extraction, hidden-state
access, Python Bridge changes, live activity, dependency changes, or M-020 work.

## Acceptance Criteria

- Only non-empty M-018 request identifiers with `bridge-assisted` mode are accepted.
- The result carries only existing raw bridge fields; `screenshot_id` comes only from the request.
- Unknown, forbidden, and provenance-override visible-surface fields fail closed.
- The builder remains pure and contains no hidden game-state, I/O, timer, network, or input access.

## Verification

Run focused bridge tests, full pytest, Ruff, format, diff, CLI-help, source-scope checks, and
independent review. Contract tests are source/Python-sanitizer based; no Node tooling is added.

## Git Handoff

Use `codex/m019-request-bound-bridge-payload`; explicitly stage intended files, commit, push, create
a complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this requires hidden game reads, filesystem polling, a new dependency, or
changes to existing Python Bridge/sanitizer contracts.
