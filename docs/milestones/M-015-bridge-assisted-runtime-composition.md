---
id: M-015
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m015-bridge-assisted-runtime
canonical_phase: D
legacy_working_label: null
---

# M-015 — Bridge-Assisted Runtime Composition

## Outcome

Add a top-level composition root joining the local JSONL bridge feed, existing screenshot-evidence-synchronized bridge observations, and the existing bounded hierarchical replan loop.

## Scope

- Construct the concrete feed and screenshot lookup from caller-supplied paths.
- Fix the bridge observation mode to `bridge-assisted`.
- Delegate unchanged to the configured bounded loop and return its exact result with audit paths.

## Out of Scope

- Input/focus construction, feed writing or polling, evidence production, producer/network/live-runtime work, CLI exposure, and M-016.

## Acceptance Criteria

- Existing bridge firewall and screenshot synchronization errors propagate unchanged.
- Loop configuration, orchestration, input executor, memory, IDs, and timestamp pass through exactly.
- Deterministic JSONL/FakeLLM/DryRun composition proves the full existing hierarchy path.

## Verification

Run focused baseline/final tests, dependency checks, full pytest, Ruff, diff, CLI-help validation, and read-only review.

## Git Handoff

Use `codex/m015-bridge-assisted-runtime`; explicitly stage intended files, commit, push, create a complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs existing bridge, Manager, loop, input, sanitizer, evidence, dependency, canonical, or live-runtime changes.
