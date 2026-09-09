---
atlas_id: CON-PLANNER-OUTPUT
atlas_type: Contract
atlas_name: PlannerOutput
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 18
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
- '[[Evidence/EVID-48-PLANNER-OUTPUT — Planner Output — baseline inspection|EVID-48-PLANNER-OUTPUT
  · Planner Output — baseline inspection]]'
- '[[Evidence/EVID-GH-CORTEX-OUTPUT — EVID-GH-CORTEX-OUTPUT|EVID-GH-CORTEX-OUTPUT
  · EVID-GH-CORTEX-OUTPUT]]'
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

# CON-PLANNER-OUTPUT — PlannerOutput

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

PlannerOutput

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `consumes` → [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `supplies` → [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- [[Evidence/EVID-48-PLANNER-OUTPUT — Planner Output — baseline inspection|EVID-48-PLANNER-OUTPUT · Planner Output — baseline inspection]] — `supports` → [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- [[Evidence/EVID-GH-CORTEX-OUTPUT — EVID-GH-CORTEX-OUTPUT|EVID-GH-CORTEX-OUTPUT · EVID-GH-CORTEX-OUTPUT]] — `supports` → [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

[[Home/Research Atlas|Research Atlas Home]]
