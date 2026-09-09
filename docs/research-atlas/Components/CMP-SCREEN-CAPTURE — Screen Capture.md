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

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-ENV-ACQUISITION — Environment & Acquisition|DOM-ENV-ACQUISITION · Environment & Acquisition]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Output: [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]

## Interfaces and contracts

None mapped.

## Data artifacts

- Output: [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical Ingress]]
- Supporting: [[Evidence/EVID-48-CAPTURE — Capture — baseline inspection|EVID-48-CAPTURE · Capture — baseline inspection]]

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
