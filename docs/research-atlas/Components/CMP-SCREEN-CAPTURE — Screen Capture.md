---
atlas_id: CMP-SCREEN-CAPTURE
atlas_type: Component
atlas_name: Screen Capture
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 26
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
observes:
- '[[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE
  · Game / Environment]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-ENV-ACQUISITION — Environment & Acquisition|DOM-ENV-ACQUISITION
  · Environment & Acquisition]]'
supplies:
- '[[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical
  Ingress]]'
- '[[Evidence/EVID-48-CAPTURE — Capture — baseline inspection|EVID-48-CAPTURE · Capture
  — baseline inspection]]'
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

# CMP-SCREEN-CAPTURE — Screen Capture

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Visible RGB capture through an explicit subprocess PPM adapter with timeout and payload validation; does not interpret pixels.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]] — `observes` → [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]
- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]] — `presented_in_domain` → [[Architecture/Domains/DOM-ENV-ACQUISITION — Environment & Acquisition|DOM-ENV-ACQUISITION · Environment & Acquisition]]
- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]] — `supplies` → [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]
- [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical Ingress]] — `supports` → [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]]
- [[Evidence/EVID-48-CAPTURE — Capture — baseline inspection|EVID-48-CAPTURE · Capture — baseline inspection]] — `supports` → [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]]

[[Home/Research Atlas|Research Atlas Home]]
