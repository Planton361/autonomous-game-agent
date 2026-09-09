---
atlas_id: CON-SKILL-CONTRACT
atlas_type: Contract
atlas_name: TaskSpec / bounded Skill Contract
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 19
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
constrains:
- '[[Components/CMP-BODY — Body|CMP-BODY · Body]]'
- '[[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]'
executes_from:
- '[[Components/CMP-BODY — Body|CMP-BODY · Body]]'
grounds_from:
- '[[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]'
supplies_from:
- '[[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]'
supports_from: &id001
- '[[Evidence/EVID-48-TASK — Task — baseline inspection|EVID-48-TASK · Task — baseline
  inspection]]'
- '[[Evidence/EVID-GH-MANAGER-SPEC — EVID-GH-MANAGER-SPEC|EVID-GH-MANAGER-SPEC · EVID-GH-MANAGER-SPEC]]'
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
research_threads:
- '[[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001
  · Experience to Action]]'
---

# CON-SKILL-CONTRACT — TaskSpec / bounded Skill Contract

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

TaskSpec / bounded Skill Contract

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]] — `constrains` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]] — `constrains` → [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]
- [[Components/CMP-BODY — Body|CMP-BODY · Body]] — `executes` → [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]] — `grounds` → [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `supplies` → [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- [[Evidence/EVID-48-TASK — Task — baseline inspection|EVID-48-TASK · Task — baseline inspection]] — `supports` → [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- [[Evidence/EVID-GH-MANAGER-SPEC — EVID-GH-MANAGER-SPEC|EVID-GH-MANAGER-SPEC · EVID-GH-MANAGER-SPEC]] — `supports` → [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

[[Home/Research Atlas|Research Atlas Home]]
