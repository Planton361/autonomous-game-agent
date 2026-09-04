---
id: M-014
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m014-jsonl-bridge-payload-source
canonical_phase: D
legacy_working_label: null
---

# M-014 — Local JSONL Bridge Payload Feed

## Outcome

Add a local append-only JSONL implementation of the existing raw bridge-payload boundary. It provides ordered decoded JSON objects to the existing bridge observation, firewall, and evidence-synchronization boundaries.

## Scope

- Add a byte-offset JSONL source with strict UTF-8, JSON-object, complete-line, and append-only checks.
- Preserve raw payload fields for downstream validation.
- Prove EOF append recovery and composition with the existing bridge observation path.

## Out of Scope

- Game producer, polling, listeners, network transport, live smoke/input, evidence creation, persistent memory, and M-015.

## Acceptance Criteria

- Construction performs no I/O; only a complete accepted physical line advances the offset.
- Partial, malformed, invalid-UTF-8, and non-object records fail without bypassing downstream security boundaries.
- Feed truncation or disappearance after consumption fails closed.
- Raw forbidden and unknown fields reach the existing sanitizer unchanged.

## Verification

Run focused baseline/final tests, source dependency checks, full pytest, Ruff, diff, CLI-help validation, and read-only review.

## Git Handoff

Use `codex/m014-jsonl-bridge-payload-source`; explicitly stage intended files, commit, push, create a complete Draft PR, and do not merge.

## Stop Conditions

Stop for Steward review if this needs a Bridge protocol, sanitizer, firewall, observation, evidence, dependency, canonical, or live-runtime change.
