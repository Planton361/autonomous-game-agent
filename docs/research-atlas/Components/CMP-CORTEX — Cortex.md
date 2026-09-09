---
atlas_id: CMP-CORTEX
atlas_type: Component
atlas_name: Cortex
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 10
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: integration-tested
consumes:
- '[[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT
  · CortexContext]]'
- '[[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]'
- '[[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT
  · Bounded retrieval snapshot (target only)]]'
- '[[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory
  to Cortex]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-COGNITION — Cognition|DOM-COGNITION · Cognition]]'
proposes_to:
- '[[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]'
related_to_research_question: &id002
- '[[Research Questions/RQ-PROGRAM-AB-001 — Program A–B working question|RQ-PROGRAM-AB-001
  · Program A–B working question]]'
supplies:
- '[[Interfaces & Contracts/CON-MEMORY-UPDATE-REQUEST — MemoryUpdateRequest|CON-MEMORY-UPDATE-REQUEST
  · MemoryUpdateRequest]]'
- '[[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT
  · PlannerOutput]]'
- '[[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT
  · PostMortemOutput]]'
- '[[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER
  · Cortex to Manager]]'
constrains_from:
- '[[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT
  · CortexContext]]'
measured_at_from:
- '[[Measurements/MEAS-CORTEX-PROPOSAL-001 — Produced PlannerOutput|MEAS-CORTEX-PROPOSAL-001
  · Produced PlannerOutput]]'
supports_from: &id001
- '[[Decisions/DEC-ATLAS-PILOT-001 — Approved Atlas pilot scope|DEC-ATLAS-PILOT-001
  · Approved Atlas pilot scope]]'
- '[[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context
  — baseline inspection]]'
- '[[Evidence/EVID-48-CORTEX — Cortex — baseline inspection|EVID-48-CORTEX · Cortex
  — baseline inspection]]'
- '[[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING
  · Test Grounding — baseline inspection]]'
- '[[Evidence/EVID-CANON-CORTEX — EVID-CANON-CORTEX|EVID-CANON-CORTEX · EVID-CANON-CORTEX]]'
- '[[Evidence/EVID-GH-CORTEX-CONTEXT — EVID-GH-CORTEX-CONTEXT|EVID-GH-CORTEX-CONTEXT
  · EVID-GH-CORTEX-CONTEXT]]'
- '[[Evidence/EVID-GH-CORTEX-INTEGRATION — EVID-GH-CORTEX-INTEGRATION|EVID-GH-CORTEX-INTEGRATION
  · EVID-GH-CORTEX-INTEGRATION]]'
- '[[Evidence/EVID-GH-CORTEX-OUTPUT — EVID-GH-CORTEX-OUTPUT|EVID-GH-CORTEX-OUTPUT
  · EVID-GH-CORTEX-OUTPUT]]'
- '[[Evidence/EVID-GH-CORTEX-PLAN — EVID-GH-CORTEX-PLAN|EVID-GH-CORTEX-PLAN · EVID-GH-CORTEX-PLAN]]'
- '[[Evidence/EVID-GH-CORTEX-PROVIDER — EVID-GH-CORTEX-PROVIDER|EVID-GH-CORTEX-PROVIDER
  · EVID-GH-CORTEX-PROVIDER]]'
- '[[Evidence/EVID-GH-CORTEX-TEST — EVID-GH-CORTEX-TEST|EVID-GH-CORTEX-TEST · EVID-GH-CORTEX-TEST]]'
measured_at: []
studied_by: []
supersedes: []
supersedes_from: []
decomposed_into: []
decomposed_into_from: []
contradicts: []
supported_by: *id001
contradicted_by: []
research_questions: *id002
research_components: []
research_interfaces: []
research_threads:
- '[[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001
  · Experience to Action]]'
---

# CMP-CORTEX — Cortex

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Slow evidence-grounded planner: consumes bounded context and proposes typed goals and constraints to Manager. Primitive control is outside its authority.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: integration-tested.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]] — `constrains` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `consumes` → [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `consumes` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `consumes` → [[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT · Bounded retrieval snapshot (target only)]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `consumes` → [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]
- [[Measurements/MEAS-CORTEX-PROPOSAL-001 — Produced PlannerOutput|MEAS-CORTEX-PROPOSAL-001 · Produced PlannerOutput]] — `measured_at` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `presented_in_domain` → [[Architecture/Domains/DOM-COGNITION — Cognition|DOM-COGNITION · Cognition]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `proposes_to` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `related_to_research_question` → [[Research Questions/RQ-PROGRAM-AB-001 — Program A–B working question|RQ-PROGRAM-AB-001 · Program A–B working question]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `supplies` → [[Interfaces & Contracts/CON-MEMORY-UPDATE-REQUEST — MemoryUpdateRequest|CON-MEMORY-UPDATE-REQUEST · MemoryUpdateRequest]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `supplies` → [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `supplies` → [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `supplies` → [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]
- [[Decisions/DEC-ATLAS-PILOT-001 — Approved Atlas pilot scope|DEC-ATLAS-PILOT-001 · Approved Atlas pilot scope]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-48-CORTEX — Cortex — baseline inspection|EVID-48-CORTEX · Cortex — baseline inspection]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING · Test Grounding — baseline inspection]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-CANON-CORTEX — EVID-CANON-CORTEX|EVID-CANON-CORTEX · EVID-CANON-CORTEX]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-GH-CORTEX-CONTEXT — EVID-GH-CORTEX-CONTEXT|EVID-GH-CORTEX-CONTEXT · EVID-GH-CORTEX-CONTEXT]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-GH-CORTEX-INTEGRATION — EVID-GH-CORTEX-INTEGRATION|EVID-GH-CORTEX-INTEGRATION · EVID-GH-CORTEX-INTEGRATION]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-GH-CORTEX-OUTPUT — EVID-GH-CORTEX-OUTPUT|EVID-GH-CORTEX-OUTPUT · EVID-GH-CORTEX-OUTPUT]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-GH-CORTEX-PLAN — EVID-GH-CORTEX-PLAN|EVID-GH-CORTEX-PLAN · EVID-GH-CORTEX-PLAN]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-GH-CORTEX-PROVIDER — EVID-GH-CORTEX-PROVIDER|EVID-GH-CORTEX-PROVIDER · EVID-GH-CORTEX-PROVIDER]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-GH-CORTEX-TEST — EVID-GH-CORTEX-TEST|EVID-GH-CORTEX-TEST · EVID-GH-CORTEX-TEST]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

[[Home/Research Atlas|Research Atlas Home]]
