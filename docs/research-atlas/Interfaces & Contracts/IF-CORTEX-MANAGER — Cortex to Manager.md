---
atlas_id: IF-CORTEX-MANAGER
atlas_type: Interface
atlas_name: Cortex to Manager
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 16
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
consumes_from:
- '[[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]'
supplies_from:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
supports_from: &id001
- '[[Evidence/EVID-48-CORTEX — Cortex — baseline inspection|EVID-48-CORTEX · Cortex
  — baseline inspection]]'
- '[[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION
  · Submission — baseline inspection]]'
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

# IF-CORTEX-MANAGER — Cortex to Manager

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Cortex to Manager

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `consumes` → [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `supplies` → [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]
- [[Evidence/EVID-48-CORTEX — Cortex — baseline inspection|EVID-48-CORTEX · Cortex — baseline inspection]] — `supports` → [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]
- [[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION · Submission — baseline inspection]] — `supports` → [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

[[Home/Research Atlas|Research Atlas Home]]
