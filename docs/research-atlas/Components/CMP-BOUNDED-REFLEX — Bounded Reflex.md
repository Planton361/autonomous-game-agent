---
atlas_id: CMP-BOUNDED-REFLEX
atlas_type: Component
atlas_name: Bounded Reflex
atlas_level: L3
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: expansion
overview_order: 46
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: target-only
verification_status: unverified
part_of:
- '[[Components/CMP-BODY — Body|CMP-BODY · Body]]'
supplies:
- '[[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION
  · Primitive Action Vocabulary]]'
constrains_from:
- '[[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT
  · TaskSpec / bounded Skill Contract]]'
supports_from: &id001
- '[[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline
  inspection]]'
- '[[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]'
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

# CMP-BOUNDED-REFLEX — Bounded Reflex

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Canonical fast Body path restricted to Manager-declared triggers and contract permissions. No separate current executable reflex path was found; ordinary heuristic action selection is not relabeled Reflex.

## Classification

Architecture authority: canonical-target. Implementation: target-only. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]] — `constrains` → [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]
- [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]] — `part_of` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]] — `supplies` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline inspection]] — `supports` → [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]
- [[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]] — `supports` → [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]

[[Home/Research Atlas|Research Atlas Home]]
