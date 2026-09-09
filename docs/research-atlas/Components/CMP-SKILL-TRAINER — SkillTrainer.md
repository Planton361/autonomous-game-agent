---
atlas_id: CMP-SKILL-TRAINER
atlas_type: Component
atlas_name: SkillTrainer
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 58
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: target-only
verification_status: unverified
consumes:
- '[[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION
  · ReplayTransition]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN
  · Verification & Learning]]'
supplies:
- '[[Data Artifacts/DAT-CANDIDATE-BODY-VERSION — Candidate Body Version|DAT-CANDIDATE-BODY-VERSION
  · Candidate Body Version]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-LEARNING — Canonical Learning|EVID-48-CANON-LEARNING ·
  Canonical Learning]]'
- '[[Evidence/EVID-48-TRAINING-LIMIT — Training Limit — baseline inspection|EVID-48-TRAINING-LIMIT
  · Training Limit — baseline inspection]]'
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

# CMP-SKILL-TRAINER — SkillTrainer

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Between runs only: canonical trainer. Current behavior_cloning helpers build datasets; no candidate-training or deployment implementation is established.

## Classification

Architecture authority: canonical-target. Implementation: target-only. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]] — `consumes` → [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]
- [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]] — `presented_in_domain` → [[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN · Verification & Learning]]
- [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]] — `supplies` → [[Data Artifacts/DAT-CANDIDATE-BODY-VERSION — Candidate Body Version|DAT-CANDIDATE-BODY-VERSION · Candidate Body Version]]
- [[Evidence/EVID-48-CANON-LEARNING — Canonical Learning|EVID-48-CANON-LEARNING · Canonical Learning]] — `supports` → [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]]
- [[Evidence/EVID-48-TRAINING-LIMIT — Training Limit — baseline inspection|EVID-48-TRAINING-LIMIT · Training Limit — baseline inspection]] — `supports` → [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]]

[[Home/Research Atlas|Research Atlas Home]]
