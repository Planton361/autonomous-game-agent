---
atlas_id: DAT-OBSERVATION
atlas_type: DataArtifact
atlas_name: Observation
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 31
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
presented_in_domain:
- '[[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|DOM-OBS-INTEGRITY-STATE
  · Observation Integrity & State]]'
consumes_from:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
- '[[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER
  · Independent Verifier]]'
- '[[Components/CMP-MEMORY — Memory|CMP-MEMORY · Memory]]'
- '[[Components/CMP-TEMPORAL-STATE — Temporal State|CMP-TEMPORAL-STATE · Temporal
  State]]'
supplies_from:
- '[[Components/CMP-PERCEPTION — Perception|CMP-PERCEPTION · Perception]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical
  Ingress]]'
- '[[Evidence/EVID-48-OBSERVATION — Observation — baseline inspection|EVID-48-OBSERVATION
  · Observation — baseline inspection]]'
- '[[Evidence/EVID-48-TEST-OBSERVATION — Test Observation — baseline inspection|EVID-48-TEST-OBSERVATION
  · Test Observation — baseline inspection]]'
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

# DAT-OBSERVATION — Observation

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Typed visible observation payload with screenshot/evidence references, UI, text, spatial signals and last action result.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

None mapped.

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|DOM-OBS-INTEGRITY-STATE · Observation Integrity & State]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Consumed by: [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- Consumed by: [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]]
- Consumed by: [[Components/CMP-MEMORY — Memory|CMP-MEMORY · Memory]]
- Consumed by: [[Components/CMP-TEMPORAL-STATE — Temporal State|CMP-TEMPORAL-STATE · Temporal State]]
- Supplied by: [[Components/CMP-PERCEPTION — Perception|CMP-PERCEPTION · Perception]]

## Interfaces and contracts

None mapped.

## Data artifacts

None mapped.

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical Ingress]]
- Supporting: [[Evidence/EVID-48-OBSERVATION — Observation — baseline inspection|EVID-48-OBSERVATION · Observation — baseline inspection]]
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
