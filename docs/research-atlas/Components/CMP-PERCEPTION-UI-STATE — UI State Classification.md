---
atlas_id: CMP-PERCEPTION-UI-STATE
atlas_type: Component
atlas_name: UI State Classification
atlas_level: L3
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: expansion
overview_order: 33
research_mapping: unmapped
research_direction: null
architecture_authority: implementation-derived
implementation_status: implemented
verification_status: unverified
part_of:
- '[[Components/CMP-PERCEPTION — Perception|CMP-PERCEPTION · Perception]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|DOM-OBS-INTEGRITY-STATE
  · Observation Integrity & State]]'
supports_from: &id001
- '[[Evidence/EVID-48-UI — Ui — baseline inspection|EVID-48-UI · Ui — baseline inspection]]'
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

# CMP-PERCEPTION-UI-STATE — UI State Classification

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

classify_ui_state implements deterministic classification from sanitized visible UI fields and OCR spans; unknown when insufficient. This is a code-derived responsibility used by ObservationBuilder, not a validated pixel classifier.

## Classification

Architecture authority: implementation-derived. Implementation: implemented. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Components/CMP-PERCEPTION — Perception|CMP-PERCEPTION · Perception]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|DOM-OBS-INTEGRITY-STATE · Observation Integrity & State]]

L-level: L3. Overview visibility: expansion.

## Inputs and outputs

None mapped.

## Interfaces and contracts

None mapped.

## Data artifacts

None mapped.

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-UI — Ui — baseline inspection|EVID-48-UI · Ui — baseline inspection]]

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
