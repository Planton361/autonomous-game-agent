---
atlas_id: CMP-INDEPENDENT-VERIFIER
atlas_type: Component
atlas_name: Independent Verifier
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 52
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
consumes:
- '[[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]'
observes:
- '[[Data Artifacts/DAT-VISIBLE-OUTCOME — Visible Outcome|DAT-VISIBLE-OUTCOME · Visible
  Outcome]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN
  · Verification & Learning]]'
supplies:
- '[[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT
  · VerifierResult]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-VERIFY — Canonical Verify|EVID-48-CANON-VERIFY · Canonical
  Verify]]'
- '[[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER
  · Skill Runner — baseline inspection]]'
- '[[Evidence/EVID-48-VERIFIER — Verifier — baseline inspection|EVID-48-VERIFIER ·
  Verifier — baseline inspection]]'
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

# CMP-INDEPENDENT-VERIFIER — Independent Verifier

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Deterministic reach-target, dialogue and interaction outcome evaluators return canonical VerifierResult. Independent of Cortex reflection; screenshot change alone is not success.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN · Verification & Learning]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Input: [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- Output: [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]

## Interfaces and contracts

- Output: [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]

## Data artifacts

- Input: [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- observes: [[Data Artifacts/DAT-VISIBLE-OUTCOME — Visible Outcome|DAT-VISIBLE-OUTCOME · Visible Outcome]]

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-CANON-VERIFY — Canonical Verify|EVID-48-CANON-VERIFY · Canonical Verify]]
- Supporting: [[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER · Skill Runner — baseline inspection]]
- Supporting: [[Evidence/EVID-48-VERIFIER — Verifier — baseline inspection|EVID-48-VERIFIER · Verifier — baseline inspection]]

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
