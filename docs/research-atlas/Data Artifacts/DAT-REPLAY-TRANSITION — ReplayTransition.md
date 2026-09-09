---
atlas_id: DAT-REPLAY-TRANSITION
atlas_type: DataArtifact
atlas_name: ReplayTransition
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: expansion
overview_order: 57
research_mapping: unmapped
research_direction: null
architecture_authority: implementation-derived
implementation_status: implemented
verification_status: unverified
presented_in_domain:
- '[[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN
  · Verification & Learning]]'
consumes_from:
- '[[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]]'
supplies_from:
- '[[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]]'
supports_from: &id001
- '[[Evidence/EVID-48-TEST-REPLAY — Test Replay — baseline inspection|EVID-48-TEST-REPLAY
  · Test Replay — baseline inspection]]'
- '[[Evidence/EVID-48-TRANSITION — Transition — baseline inspection|EVID-48-TRANSITION
  · Transition — baseline inspection]]'
part_of: []
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

# DAT-REPLAY-TRANSITION — ReplayTransition

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Synthetic obs/action/reward/next_obs/done/task/metadata payload with recursive forbidden-key checks. Does not imply full official-run provenance or training eligibility.

## Classification

Architecture authority: implementation-derived. Implementation: implemented. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

None mapped.

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN · Verification & Learning]]

L-level: L2. Overview visibility: expansion.

## Inputs and outputs

- Consumed by: [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]]
- Supplied by: [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]]

## Interfaces and contracts

None mapped.

## Data artifacts

None mapped.

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-TEST-REPLAY — Test Replay — baseline inspection|EVID-48-TEST-REPLAY · Test Replay — baseline inspection]]
- Supporting: [[Evidence/EVID-48-TRANSITION — Transition — baseline inspection|EVID-48-TRANSITION · Transition — baseline inspection]]

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
