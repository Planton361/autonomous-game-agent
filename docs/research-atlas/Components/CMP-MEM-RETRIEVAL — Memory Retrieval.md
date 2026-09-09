---
atlas_id: CMP-MEM-RETRIEVAL
atlas_type: Component
atlas_name: Memory Retrieval
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 9
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY
  · Evidence, Memory & Retrieval]]'
related_to_research_question: &id002
- '[[Research Questions/RQ-PROGRAM-AB-001 — Program A–B working question|RQ-PROGRAM-AB-001
  · Program A–B working question]]'
supplies:
- '[[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT
  · Bounded retrieval snapshot (target only)]]'
- '[[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory
  to Cortex]]'
constrains_from:
- '[[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT
  · CortexContext]]'
measured_at_from:
- '[[Measurements/MEAS-RETRIEVAL-DELIVERY-001 — Actual memory-evidence delivered to
  Cortex|MEAS-RETRIEVAL-DELIVERY-001 · Actual memory/evidence delivered to Cortex]]'
supports_from: &id001
- '[[Decisions/DEC-ATLAS-PILOT-001 — Approved Atlas pilot scope|DEC-ATLAS-PILOT-001
  · Approved Atlas pilot scope]]'
- '[[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context
  — baseline inspection]]'
- '[[Evidence/EVID-48-MEMORY — Memory — baseline inspection|EVID-48-MEMORY · Memory
  — baseline inspection]]'
- '[[Evidence/EVID-CANON-MEM — EVID-CANON-MEM|EVID-CANON-MEM · EVID-CANON-MEM]]'
- '[[Evidence/EVID-GH-MEM-CONTEXT — EVID-GH-MEM-CONTEXT|EVID-GH-MEM-CONTEXT · EVID-GH-MEM-CONTEXT]]'
- '[[Evidence/EVID-GH-MEM-DB — EVID-GH-MEM-DB|EVID-GH-MEM-DB · EVID-GH-MEM-DB]]'
- '[[Evidence/EVID-GH-MEM-FACTS — EVID-GH-MEM-FACTS|EVID-GH-MEM-FACTS · EVID-GH-MEM-FACTS]]'
- '[[Evidence/EVID-GH-MEM-TEST — EVID-GH-MEM-TEST|EVID-GH-MEM-TEST · EVID-GH-MEM-TEST]]'
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

# CMP-MEM-RETRIEVAL — Memory Retrieval

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Cortex should receive a bounded snapshot of admissible memory. Persistence and evidence-backed facts exist; caller-supplied memory_summary reaches context assembly. A dedicated retriever, versioned RetrievalSnapshot, and ranking/eligibility retrieval are not established.

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY · Evidence, Memory & Retrieval]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Output: [[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT · Bounded retrieval snapshot (target only)]]
- Output: [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]

## Interfaces and contracts

- Constrained by: [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- Output: [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]

## Data artifacts

- Output: [[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT · Bounded retrieval snapshot (target only)]]

## Measurement points

- Measurement point: [[Measurements/MEAS-RETRIEVAL-DELIVERY-001 — Actual memory-evidence delivered to Cortex|MEAS-RETRIEVAL-DELIVERY-001 · Actual memory/evidence delivered to Cortex]]

## Evidence

- Supporting: [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]]
- Supporting: [[Evidence/EVID-48-MEMORY — Memory — baseline inspection|EVID-48-MEMORY · Memory — baseline inspection]]
- Supporting: [[Evidence/EVID-CANON-MEM — EVID-CANON-MEM|EVID-CANON-MEM · EVID-CANON-MEM]]
- Supporting: [[Evidence/EVID-GH-MEM-CONTEXT — EVID-GH-MEM-CONTEXT|EVID-GH-MEM-CONTEXT · EVID-GH-MEM-CONTEXT]]
- Supporting: [[Evidence/EVID-GH-MEM-DB — EVID-GH-MEM-DB|EVID-GH-MEM-DB · EVID-GH-MEM-DB]]
- Supporting: [[Evidence/EVID-GH-MEM-FACTS — EVID-GH-MEM-FACTS|EVID-GH-MEM-FACTS · EVID-GH-MEM-FACTS]]
- Supporting: [[Evidence/EVID-GH-MEM-TEST — EVID-GH-MEM-TEST|EVID-GH-MEM-TEST · EVID-GH-MEM-TEST]]

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
