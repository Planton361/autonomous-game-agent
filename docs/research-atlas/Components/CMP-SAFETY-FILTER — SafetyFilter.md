---
atlas_id: CMP-SAFETY-FILTER
atlas_type: Component
atlas_name: SafetyFilter
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 48
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
consumes:
- '[[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION
  · Primitive Action Vocabulary]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY ·
  Action & Safety]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]'
- '[[Evidence/EVID-48-SAFETY — Safety — baseline inspection|EVID-48-SAFETY · Safety
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

# CMP-SAFETY-FILTER — SafetyFilter

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Pure SafetyFilter assesses synthetic movement candidates against supplied hazard signals. Full visible hazard acquisition and a universal runtime risk boundary are not established by this navigation filter.

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-SAFETY-FILTER — SafetyFilter|CMP-SAFETY-FILTER · SafetyFilter]] — `consumes` → [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Components/CMP-SAFETY-FILTER — SafetyFilter|CMP-SAFETY-FILTER · SafetyFilter]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-SAFETY-FILTER — SafetyFilter|CMP-SAFETY-FILTER · SafetyFilter]] — `presented_in_domain` → [[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY · Action & Safety]]
- [[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]] — `supports` → [[Components/CMP-SAFETY-FILTER — SafetyFilter|CMP-SAFETY-FILTER · SafetyFilter]]
- [[Evidence/EVID-48-SAFETY — Safety — baseline inspection|EVID-48-SAFETY · Safety — baseline inspection]] — `supports` → [[Components/CMP-SAFETY-FILTER — SafetyFilter|CMP-SAFETY-FILTER · SafetyFilter]]

[[Home/Research Atlas|Research Atlas Home]]
