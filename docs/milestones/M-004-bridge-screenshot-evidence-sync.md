---
id: M-004
status: done
risk: medium
model_profile: standard
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m004-bridge-screenshot-evidence-sync
canonical_phase: D
legacy_working_label: null
---

# M-004 — Bridge-assisted Screenshot Evidence Synchronization

## Outcome

Require every `bridge-assisted` Observation to match the latest durable screenshot evidence ID for its run before it leaves the bridge source.

## Scope

- Add a small read-only bridge-facing screenshot-evidence lookup backed by existing event-log reads.
- Gate `BridgeObservationSource` after adapter validation and run-mode containment.
- Preserve one-payload observation semantics, firewall errors, canonical Observation behavior, and debug-mode behavior.
- Add deterministic lookup, synchronization, stale-ID, and guarded `SkillRunner` coverage.
- Record M-004 completion in the operational roadmap and session report.

## Out of Scope

- event-log, EvidenceStore, or CaptureSession changes
- image inspection, OCR, CV, VLM, semantic bridge-to-image validation, success inference, or reward
- live transport, game launch, real input, Cortex, Manager, global run-mode work, dependencies, and M-005

## Acceptance Criteria

- Bridge-assisted construction requires an explicit screenshot-evidence lookup without consuming payloads or reading the log.
- A bridge-assisted payload needs a non-empty screenshot ID exactly equal to the run's latest valid durable screenshot evidence ID.
- Missing, fabricated, and stale IDs fail with a distinct bridge synchronization error.
- Debug remains optional for evidence lookup and may omit screenshots.
- Existing sanitizer/firewall and run-mode errors remain distinct; no evidence is mutated.
- Synchronized raw bridge payloads drive the unchanged `SkillRunner` through `DryRunInputBackend` with before/action/after evidence linkage.

## Verification

Run focused baseline and final suites, dependency-direction searches, fresh full pytest, Ruff, diff check, and CLI help. Inspect changed paths and protected zero diffs.

## Git Handoff

Use the declared A2 branch, explicitly stage intended files, commit, push, create a Draft PR, and leave merge to the user.

## Stop Conditions

Stop for missing M-003 merge, dirty workspace, required EventLogger/CaptureSession redesign, image inspection or semantic validation, Observation-schema or sanitizer change, live transport, Manager/Cortex integration, new dependency, canonical revision, untrustworthy validation, or three failed focused fixes.
