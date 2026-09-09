---
atlas_id: CMP-INPUT-EXECUTOR
atlas_type: Component
atlas_name: InputExecutor
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 49
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
consumes:
- '[[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION
  · Primitive Action Vocabulary]]'
controls:
- '[[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE
  · Game / Environment]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY ·
  Action & Safety]]'
supplies:
- '[[Data Artifacts/DAT-ACTION-RESULT — ActionResult|DAT-ACTION-RESULT · ActionResult]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]'
- '[[Evidence/EVID-48-INPUT — Input — baseline inspection|EVID-48-INPUT · Input —
  baseline inspection]]'
- '[[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER
  · Skill Runner — baseline inspection]]'
- '[[Evidence/EVID-48-TASK-EXECUTOR — Task Executor — baseline inspection|EVID-48-TASK-EXECUTOR
  · Task Executor — baseline inspection]]'
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

# CMP-INPUT-EXECUTOR — InputExecutor

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Separate primitive-input boundary enforcing target focus, rate limit and emergency stop. Active-task checks and action masks belong to Manager execution composition; transition logging is supplied when configured. This class alone does not establish all canonical input preconditions.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]] — `consumes` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]] — `controls` → [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]
- [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]] — `presented_in_domain` → [[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY · Action & Safety]]
- [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]] — `supplies` → [[Data Artifacts/DAT-ACTION-RESULT — ActionResult|DAT-ACTION-RESULT · ActionResult]]
- [[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]] — `supports` → [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]]
- [[Evidence/EVID-48-INPUT — Input — baseline inspection|EVID-48-INPUT · Input — baseline inspection]] — `supports` → [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]]
- [[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER · Skill Runner — baseline inspection]] — `supports` → [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]]
- [[Evidence/EVID-48-TASK-EXECUTOR — Task Executor — baseline inspection|EVID-48-TASK-EXECUTOR · Task Executor — baseline inspection]] — `supports` → [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]]

[[Home/Research Atlas|Research Atlas Home]]
