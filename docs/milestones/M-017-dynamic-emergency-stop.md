---
id: M-017
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m017-dynamic-emergency-stop
canonical_phase: D
legacy_working_label: null
---

# M-017 — Dynamic Emergency-Stop Gate

## Outcome

Add a fail-closed dynamic emergency-stop source to the existing InputExecutor safety path.

## Scope

- Add a structural `EmergencyStopCheck` port and a caller-owned stop-file implementation.
- Probe the dynamic source before focus and rate-limit checks for every action.
- Preserve manual stop controls and existing ManagerStop mapping.

## Out of Scope

No Manager, Body, Bridge, Xdotool, runtime composition, CLI, controlled-live-smoke, live input,
polling, emergency-stop redesign, or M-018 work.

## Acceptance Criteria

- Stop-file presence and probe errors stop input; absence permits normal guarded execution.
- Manual and external stops are both fail-closed, and clearing the manual latch cannot bypass an
  active external stop.
- Existing SkillRunner behavior produces the established safety-intervention ManagerStop result.

## Verification

Run focused safety/SkillRunner tests, full pytest, Ruff, formatting, diff, CLI-help, source-scope
checks, and independent review.

## Git Handoff

Use `codex/m017-dynamic-emergency-stop`; explicitly stage intended files, commit, push, create a
complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs ManagerStop semantics, Xdotool adapters, dependencies,
live-runtime/CLI work, or canonical changes.
