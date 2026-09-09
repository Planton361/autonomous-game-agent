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

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]] — `constrains` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Measurements/MEAS-RETRIEVAL-DELIVERY-001 — Actual memory-evidence delivered to Cortex|MEAS-RETRIEVAL-DELIVERY-001 · Actual memory/evidence delivered to Cortex]] — `measured_at` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]] — `presented_in_domain` → [[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY · Evidence, Memory & Retrieval]]
- [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]] — `related_to_research_question` → [[Research Questions/RQ-PROGRAM-AB-001 — Program A–B working question|RQ-PROGRAM-AB-001 · Program A–B working question]]
- [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]] — `supplies` → [[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT · Bounded retrieval snapshot (target only)]]
- [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]] — `supplies` → [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]
- [[Decisions/DEC-ATLAS-PILOT-001 — Approved Atlas pilot scope|DEC-ATLAS-PILOT-001 · Approved Atlas pilot scope]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Evidence/EVID-48-MEMORY — Memory — baseline inspection|EVID-48-MEMORY · Memory — baseline inspection]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Evidence/EVID-CANON-MEM — EVID-CANON-MEM|EVID-CANON-MEM · EVID-CANON-MEM]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Evidence/EVID-GH-MEM-CONTEXT — EVID-GH-MEM-CONTEXT|EVID-GH-MEM-CONTEXT · EVID-GH-MEM-CONTEXT]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Evidence/EVID-GH-MEM-DB — EVID-GH-MEM-DB|EVID-GH-MEM-DB · EVID-GH-MEM-DB]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Evidence/EVID-GH-MEM-FACTS — EVID-GH-MEM-FACTS|EVID-GH-MEM-FACTS · EVID-GH-MEM-FACTS]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Evidence/EVID-GH-MEM-TEST — EVID-GH-MEM-TEST|EVID-GH-MEM-TEST · EVID-GH-MEM-TEST]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

[[Home/Research Atlas|Research Atlas Home]]
