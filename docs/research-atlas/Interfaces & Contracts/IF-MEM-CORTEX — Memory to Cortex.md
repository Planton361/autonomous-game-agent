---
atlas_id: IF-MEM-CORTEX
atlas_type: Interface
atlas_name: Memory to Cortex
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 15
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
consumes_from:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
supplies_from:
- '[[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]'
supports_from: &id001
- '[[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context
  — baseline inspection]]'
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

# IF-MEM-CORTEX — Memory to Cortex

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Memory to Cortex

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `consumes` → [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]
- [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]] — `supplies` → [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]
- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

[[Home/Research Atlas|Research Atlas Home]]
