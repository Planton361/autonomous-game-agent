---
id: M-003
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m003-bridge-observation-source
canonical_phase: D
legacy_working_label: null
---

# M-003 — Bridge-assisted ObservationSource

## Outcome

Expose raw visible bridge payloads through the existing canonical `ObservationSource` boundary without changing the generic observation port, bridge firewall, Observation schema, or `SkillRunner`.

## Scope

- Add a small bridge-local raw-payload port and `BridgeObservationSource`.
- Convert exactly one payload per `observe()` through `VisibleBridgeAdapter`.
- Preserve explicit run-mode containment, canonical exhaustion semantics, and firewall error types.
- Add deterministic bridge-source and guarded `SkillRunner` integration coverage.
- Record M-003 completion in the operational roadmap and session report.

## Out of Scope

- live bridge transport, sockets, HTTP, game launch, or real input
- Cortex, Manager, task, memory, reward, or verifier changes
- Observation schema, generic `ObservationSource`, sanitizer, or bridge-server changes
- global run-mode normalization, canonical-source changes, pilot changes, dependencies, and M-004

## Acceptance Criteria

- Construction performs no payload read; each successful `observe()` pulls exactly one payload.
- The bridge adapter remains the sole sanitizer and Observation-conversion path.
- Explicit payload-source exhaustion maps to `ObservationSourceExhausted`; other errors propagate unchanged.
- One source retains its expected bridge mode and rejects a valid opposite mode.
- Raw payloads drive the existing `SkillRunner` to a verifier-backed dialogue success using only `DryRunInputBackend`.
- No live transport or hidden-state bypass is introduced.

## Verification

Run the focused baseline and final suites, dependency-direction searches, full pytest, Ruff, diff check, and CLI help. Inspect changed paths and protected zero diffs.

## Git Handoff

Use the declared A2 branch, stage intended files explicitly, commit, push, create a Draft PR, and leave merge to the user.

## Stop Conditions

Stop for missing M-002 merge, dirty workspace, required live transport, Observation-schema or `SkillRunner` change, sanitizer/firewall change, Manager/Cortex integration, global run-mode refactor, dependency need, hidden-state weakening, untrustworthy validation, or three failed focused fixes.
