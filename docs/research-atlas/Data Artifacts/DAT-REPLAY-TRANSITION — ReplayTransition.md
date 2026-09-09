---
atlas_id: DAT-REPLAY-TRANSITION
atlas_type: DataArtifact
atlas_name: ReplayTransition
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 57
research_mapping: unmapped
research_direction: null
architecture_authority: implementation-derived
implementation_status: implemented
verification_status: unverified
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

# DAT-REPLAY-TRANSITION — ReplayTransition

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Synthetic obs/action/reward/next_obs/done/task/metadata payload with recursive forbidden-key checks. Does not imply full official-run provenance or training eligibility.

## Classification

Architecture authority: implementation-derived. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]] — `consumes` → [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]
- [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]] — `supplies` → [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]
- [[Evidence/EVID-48-TEST-REPLAY — Test Replay — baseline inspection|EVID-48-TEST-REPLAY · Test Replay — baseline inspection]] — `supports` → [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]
- [[Evidence/EVID-48-TRANSITION — Transition — baseline inspection|EVID-48-TRANSITION · Transition — baseline inspection]] — `supports` → [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]

[[Home/Research Atlas|Research Atlas Home]]
