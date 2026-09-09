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

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-COGNITION — Cognition|DOM-COGNITION · Cognition]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Input: [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- Input: [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- Input: [[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT · Bounded retrieval snapshot (target only)]]
- Input: [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]
- Output: [[Interfaces & Contracts/CON-MEMORY-UPDATE-REQUEST — MemoryUpdateRequest|CON-MEMORY-UPDATE-REQUEST · MemoryUpdateRequest]]
- Output: [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- Output: [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- Output: [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]

## Interfaces and contracts

- Constrained by: [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- Input: [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- Input: [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]
- Output: [[Interfaces & Contracts/CON-MEMORY-UPDATE-REQUEST — MemoryUpdateRequest|CON-MEMORY-UPDATE-REQUEST · MemoryUpdateRequest]]
- Output: [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- Output: [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- Output: [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]

## Data artifacts

- Input: [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- Input: [[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT · Bounded retrieval snapshot (target only)]]

## Measurement points

- Measurement point: [[Measurements/MEAS-CORTEX-PROPOSAL-001 — Produced PlannerOutput|MEAS-CORTEX-PROPOSAL-001 · Produced PlannerOutput]]

## Evidence

- Supporting: [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]]
- Supporting: [[Evidence/EVID-48-CORTEX — Cortex — baseline inspection|EVID-48-CORTEX · Cortex — baseline inspection]]
- Supporting: [[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING · Test Grounding — baseline inspection]]
- Supporting: [[Evidence/EVID-CANON-CORTEX — EVID-CANON-CORTEX|EVID-CANON-CORTEX · EVID-CANON-CORTEX]]
- Supporting: [[Evidence/EVID-GH-CORTEX-CONTEXT — EVID-GH-CORTEX-CONTEXT|EVID-GH-CORTEX-CONTEXT · EVID-GH-CORTEX-CONTEXT]]
- Supporting: [[Evidence/EVID-GH-CORTEX-INTEGRATION — EVID-GH-CORTEX-INTEGRATION|EVID-GH-CORTEX-INTEGRATION · EVID-GH-CORTEX-INTEGRATION]]
- Supporting: [[Evidence/EVID-GH-CORTEX-OUTPUT — EVID-GH-CORTEX-OUTPUT|EVID-GH-CORTEX-OUTPUT · EVID-GH-CORTEX-OUTPUT]]
- Supporting: [[Evidence/EVID-GH-CORTEX-PLAN — EVID-GH-CORTEX-PLAN|EVID-GH-CORTEX-PLAN · EVID-GH-CORTEX-PLAN]]
- Supporting: [[Evidence/EVID-GH-CORTEX-PROVIDER — EVID-GH-CORTEX-PROVIDER|EVID-GH-CORTEX-PROVIDER · EVID-GH-CORTEX-PROVIDER]]
- Supporting: [[Evidence/EVID-GH-CORTEX-TEST — EVID-GH-CORTEX-TEST|EVID-GH-CORTEX-TEST · EVID-GH-CORTEX-TEST]]

## Research questions

- Research question: [[Research Questions/RQ-PROGRAM-AB-001 — Program A–B working question|RQ-PROGRAM-AB-001 · Program A–B working question]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

## Papers

None mapped.

## Findings and contradictions

None mapped.

## Decisions

- Supporting: [[Decisions/DEC-ATLAS-PILOT-001 — Approved Atlas pilot scope|DEC-ATLAS-PILOT-001 · Approved Atlas pilot scope]]

## Experiment leads

None mapped.

## History

None mapped.

Outgoing/incoming edges show supersedes / superseded by and decomposed into / from.

## Review / proposals

No accepted proposal is mapped unless represented by the Registry decisions above. Keep authored proposals in separate notes; accepted changes must enter through Registry review. Generated notes do not accept changes or claims.

[[Home/Research Atlas|Research Atlas Home]]
