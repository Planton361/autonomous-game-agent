---
atlas_id: DAT-SCREEN-FRAME
atlas_type: DataArtifact
atlas_name: ScreenFrame
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 27
research_mapping: unmapped
research_direction: null
architecture_authority: implementation-derived
implementation_status: implemented
verification_status: unverified
consumes_from:
- '[[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence
  Ledger]]'
- '[[Components/CMP-PERCEPTION — Perception|CMP-PERCEPTION · Perception]]'
supplies_from:
- '[[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]]'
supports_from: &id001
- '[[Evidence/EVID-48-FRAME — Frame — baseline inspection|EVID-48-FRAME · Frame —
  baseline inspection]]'
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

# DAT-SCREEN-FRAME — ScreenFrame

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Immutable RGB frame dimensions, pixels and capture time; validates raster size. A data artifact, not an actor.

## Classification

Architecture authority: implementation-derived. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence Ledger]] — `consumes` → [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]
- [[Components/CMP-PERCEPTION — Perception|CMP-PERCEPTION · Perception]] — `consumes` → [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]
- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]] — `supplies` → [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]
- [[Evidence/EVID-48-FRAME — Frame — baseline inspection|EVID-48-FRAME · Frame — baseline inspection]] — `supports` → [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]

[[Home/Research Atlas|Research Atlas Home]]
