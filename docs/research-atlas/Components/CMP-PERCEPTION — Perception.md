---
atlas_id: CMP-PERCEPTION
atlas_type: Component
atlas_name: Perception
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 30
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
consumes:
- '[[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|DOM-OBS-INTEGRITY-STATE
  · Observation Integrity & State]]'
supplies:
- '[[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]'
part_of_from:
- '[[Components/CMP-OBSERVATION-BUILDER — Observation Builder|CMP-OBSERVATION-BUILDER
  · Observation Builder]]'
- '[[Components/CMP-PERCEPTION-UI-STATE — UI State Classification|CMP-PERCEPTION-UI-STATE
  · UI State Classification]]'
supports_from: &id001
- '[[Evidence/EVID-48-BUILDER — Builder — baseline inspection|EVID-48-BUILDER · Builder
  — baseline inspection]]'
- '[[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical
  Ingress]]'
- '[[Evidence/EVID-48-OCR-LIMIT — Ocr Limit — baseline inspection|EVID-48-OCR-LIMIT
  · Ocr Limit — baseline inspection]]'
- '[[Evidence/EVID-48-SPATIAL-LIMIT — Spatial Limit — baseline inspection|EVID-48-SPATIAL-LIMIT
  · Spatial Limit — baseline inspection]]'
- '[[Evidence/EVID-48-TEST-OBSERVATION — Test Observation — baseline inspection|EVID-48-TEST-OBSERVATION
  · Test Observation — baseline inspection]]'
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

# CMP-PERCEPTION — Perception

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

ObservationBuilder assembles frame signatures, OCR output and UI signals. OCR backends are NoOp/Static fixtures; SpatialPerceptionProducer declares an interface, not a demonstrated pixel detector.

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical child: [[Components/CMP-OBSERVATION-BUILDER — Observation Builder|CMP-OBSERVATION-BUILDER · Observation Builder]]
- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- Technical child: [[Components/CMP-PERCEPTION-UI-STATE — UI State Classification|CMP-PERCEPTION-UI-STATE · UI State Classification]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|DOM-OBS-INTEGRITY-STATE · Observation Integrity & State]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Input: [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]
- Output: [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]

## Interfaces and contracts

None mapped.

## Data artifacts

- Input: [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]
- Output: [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-BUILDER — Builder — baseline inspection|EVID-48-BUILDER · Builder — baseline inspection]]
- Supporting: [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical Ingress]]
- Supporting: [[Evidence/EVID-48-OCR-LIMIT — Ocr Limit — baseline inspection|EVID-48-OCR-LIMIT · Ocr Limit — baseline inspection]]
- Supporting: [[Evidence/EVID-48-SPATIAL-LIMIT — Spatial Limit — baseline inspection|EVID-48-SPATIAL-LIMIT · Spatial Limit — baseline inspection]]
- Supporting: [[Evidence/EVID-48-TEST-OBSERVATION — Test Observation — baseline inspection|EVID-48-TEST-OBSERVATION · Test Observation — baseline inspection]]

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
