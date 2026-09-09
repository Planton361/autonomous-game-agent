---
atlas_id: ENV-GAME-INSTANCE
atlas_type: Environment
atlas_name: Game / Environment
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 25
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: target-only
verification_status: unverified
controls_from:
- '[[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]]'
observes_from:
- '[[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]]'
- '[[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE
  · Optional Visible-State Bridge]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical
  Ingress]]'
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

# ENV-GAME-INSTANCE — Game / Environment

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

External game instance in experiment scope, outside the Agent boundary. The existence of a game is not a repository implementation claim.

## Classification

Architecture authority: canonical-target. Implementation: target-only. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]] — `controls` → [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]
- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]] — `observes` → [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]
- [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]] — `observes` → [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]
- [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical Ingress]] — `supports` → [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]

[[Home/Research Atlas|Research Atlas Home]]
