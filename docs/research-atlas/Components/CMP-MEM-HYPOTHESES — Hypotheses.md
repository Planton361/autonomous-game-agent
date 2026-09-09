---
atlas_id: CMP-MEM-HYPOTHESES
atlas_type: Component
atlas_name: Hypotheses
atlas_level: L3
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: expansion
overview_order: 39
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
part_of:
- '[[Components/CMP-MEMORY — Memory|CMP-MEMORY · Memory]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-MEMORY — Canonical Memory|EVID-48-CANON-MEMORY · Canonical
  Memory]]'
- '[[Evidence/EVID-48-FACTS — Facts — baseline inspection|EVID-48-FACTS · Facts —
  baseline inspection]]'
- '[[Evidence/EVID-48-TEST-FACTS — Test Facts — baseline inspection|EVID-48-TEST-FACTS
  · Test Facts — baseline inspection]]'
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

# CMP-MEM-HYPOTHESES — Hypotheses

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

FactStore supports hypothesis/contradicted status and confidence. Separate supporting versus contradicting evidence, test-action lifecycle and automatic adjudication are not implemented by this API.

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-MEM-HYPOTHESES — Hypotheses|CMP-MEM-HYPOTHESES · Hypotheses]] — `part_of` → [[Components/CMP-MEMORY — Memory|CMP-MEMORY · Memory]]
- [[Evidence/EVID-48-CANON-MEMORY — Canonical Memory|EVID-48-CANON-MEMORY · Canonical Memory]] — `supports` → [[Components/CMP-MEM-HYPOTHESES — Hypotheses|CMP-MEM-HYPOTHESES · Hypotheses]]
- [[Evidence/EVID-48-FACTS — Facts — baseline inspection|EVID-48-FACTS · Facts — baseline inspection]] — `supports` → [[Components/CMP-MEM-HYPOTHESES — Hypotheses|CMP-MEM-HYPOTHESES · Hypotheses]]
- [[Evidence/EVID-48-TEST-FACTS — Test Facts — baseline inspection|EVID-48-TEST-FACTS · Test Facts — baseline inspection]] — `supports` → [[Components/CMP-MEM-HYPOTHESES — Hypotheses|CMP-MEM-HYPOTHESES · Hypotheses]]

[[Home/Research Atlas|Research Atlas Home]]
