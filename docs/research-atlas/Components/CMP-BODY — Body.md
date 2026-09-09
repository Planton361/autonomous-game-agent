---
atlas_id: CMP-BODY
atlas_type: Component
atlas_name: Body
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 45
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
executes:
- '[[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT
  · TaskSpec / bounded Skill Contract]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY ·
  Action & Safety]]'
supplies:
- '[[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION
  · Primitive Action Vocabulary]]'
constrains_from:
- '[[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT
  · TaskSpec / bounded Skill Contract]]'
controls_from:
- '[[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]'
part_of_from:
- '[[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]'
supports_from: &id001
- '[[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline
  inspection]]'
- '[[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]'
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

# CMP-BODY — Body

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Reusable heuristic skills propose one primitive at a time from visible grounded targets; ManagerTaskExecutor binds execution to an active task and SkillRunner enforces the skill action mask. Learned Body and full canonical skill breadth are not claimed.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]] — `constrains` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `controls` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Components/CMP-BODY — Body|CMP-BODY · Body]] — `executes` → [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- [[Components/CMP-BODY — Body|CMP-BODY · Body]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]] — `part_of` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Components/CMP-BODY — Body|CMP-BODY · Body]] — `presented_in_domain` → [[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY · Action & Safety]]
- [[Components/CMP-BODY — Body|CMP-BODY · Body]] — `supplies` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline inspection]] — `supports` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]] — `supports` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER · Skill Runner — baseline inspection]] — `supports` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Evidence/EVID-48-TASK-EXECUTOR — Task Executor — baseline inspection|EVID-48-TASK-EXECUTOR · Task Executor — baseline inspection]] — `supports` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]

[[Home/Research Atlas|Research Atlas Home]]
