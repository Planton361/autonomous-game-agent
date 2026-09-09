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
presented_in_domain: []
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

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `consumes` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]] — `consumes` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Components/CMP-MEMORY — Memory|CMP-MEMORY · Memory]] — `consumes` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Components/CMP-TEMPORAL-STATE — Temporal State|CMP-TEMPORAL-STATE · Temporal State]] — `consumes` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Components/CMP-PERCEPTION — Perception|CMP-PERCEPTION · Perception]] — `supplies` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical Ingress]] — `supports` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Evidence/EVID-48-OBSERVATION — Observation — baseline inspection|EVID-48-OBSERVATION · Observation — baseline inspection]] — `supports` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Evidence/EVID-48-TEST-OBSERVATION — Test Observation — baseline inspection|EVID-48-TEST-OBSERVATION · Test Observation — baseline inspection]] — `supports` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]

[[Home/Research Atlas|Research Atlas Home]]
