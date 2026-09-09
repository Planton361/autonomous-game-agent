---
atlas_id: CMP-REPLAY-BUFFER
atlas_type: Component
atlas_name: Replay Buffer
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 56
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
consumes:
- '[[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT
  · VerifierResult]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN
  · Verification & Learning]]'
supplies:
- '[[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION
  · ReplayTransition]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-VERIFY — Canonical Verify|EVID-48-CANON-VERIFY · Canonical
  Verify]]'
- '[[Evidence/EVID-48-REPLAY — Replay — baseline inspection|EVID-48-REPLAY · Replay
  — baseline inspection]]'
- '[[Evidence/EVID-48-TEST-REPLAY — Test Replay — baseline inspection|EVID-48-TEST-REPLAY
  · Test Replay — baseline inspection]]'
measured_at: []
studied_by: []
supersedes: []
supersedes_from: []
decomposed_into: []
decomposed_into_from: []
contradicts: []
supported_by: *id001
contradicted_by: []
research_questions: []
research_components: []
research_interfaces: []
research_threads: []
---

# CMP-REPLAY-BUFFER — Replay Buffer

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Fixed-capacity FIFO and seeded sampling exist for synthetic ReplayTransition objects. Complete admissible run/contract/verifier provenance and official training eligibility are not enforced by this buffer.

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN · Verification & Learning]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Input: [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- Output: [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]

## Interfaces and contracts

- Input: [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]

## Data artifacts

- Output: [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-CANON-VERIFY — Canonical Verify|EVID-48-CANON-VERIFY · Canonical Verify]]
- Supporting: [[Evidence/EVID-48-REPLAY — Replay — baseline inspection|EVID-48-REPLAY · Replay — baseline inspection]]
- Supporting: [[Evidence/EVID-48-TEST-REPLAY — Test Replay — baseline inspection|EVID-48-TEST-REPLAY · Test Replay — baseline inspection]]

## Research questions

None mapped.

## Research threads

None mapped.

## Papers

None mapped.

## Findings and contradictions

None mapped.

## Decisions

None mapped.

## Experiment leads

None mapped.

## History

None mapped.

Outgoing/incoming edges show supersedes / superseded by and decomposed into / from.

## Review / proposals

No accepted proposal is mapped unless represented by the Registry decisions above. Keep authored proposals in separate notes; accepted changes must enter through Registry review. Generated notes do not accept changes or claims.

[[Home/Research Atlas|Research Atlas Home]]
