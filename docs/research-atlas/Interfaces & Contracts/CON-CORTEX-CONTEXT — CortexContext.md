---
atlas_id: CON-CORTEX-CONTEXT
atlas_type: Contract
atlas_name: CortexContext
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 17
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
constrains:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
- '[[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]'
consumes_from:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
supports_from: &id001
- '[[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context
  — baseline inspection]]'
- '[[Evidence/EVID-GH-CORTEX-CONTEXT — EVID-GH-CORTEX-CONTEXT|EVID-GH-CORTEX-CONTEXT
  · EVID-GH-CORTEX-CONTEXT]]'
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

# CON-CORTEX-CONTEXT — CortexContext

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

CortexContext

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]] — `constrains` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]] — `constrains` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `consumes` → [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- [[Evidence/EVID-GH-CORTEX-CONTEXT — EVID-GH-CORTEX-CONTEXT|EVID-GH-CORTEX-CONTEXT · EVID-GH-CORTEX-CONTEXT]] — `supports` → [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

[[Home/Research Atlas|Research Atlas Home]]
