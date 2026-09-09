---
atlas_id: CON-PRIMITIVE-ACTION
atlas_type: Contract
atlas_name: Primitive Action Vocabulary
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 47
research_mapping: unmapped
research_direction: null
architecture_authority: implementation-derived
implementation_status: implemented
verification_status: unverified
consumes_from:
- '[[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]]'
- '[[Components/CMP-SAFETY-FILTER — SafetyFilter|CMP-SAFETY-FILTER · SafetyFilter]]'
supplies_from:
- '[[Components/CMP-BODY — Body|CMP-BODY · Body]]'
- '[[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]'
supports_from: &id001
- '[[Evidence/EVID-48-PRIMITIVE — Primitive — baseline inspection|EVID-48-PRIMITIVE
  · Primitive — baseline inspection]]'
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

# CON-PRIMITIVE-ACTION — Primitive Action Vocabulary

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Closed PrimitiveAction enum: short directional movement, confirm, cancel, open_menu and wait. Vocabulary contract; not permission to execute.

## Classification

Architecture authority: implementation-derived. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]] — `consumes` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Components/CMP-SAFETY-FILTER — SafetyFilter|CMP-SAFETY-FILTER · SafetyFilter]] — `consumes` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Components/CMP-BODY — Body|CMP-BODY · Body]] — `supplies` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]] — `supplies` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Evidence/EVID-48-PRIMITIVE — Primitive — baseline inspection|EVID-48-PRIMITIVE · Primitive — baseline inspection]] — `supports` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]

[[Home/Research Atlas|Research Atlas Home]]
