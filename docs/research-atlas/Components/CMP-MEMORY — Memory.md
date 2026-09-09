---
atlas_id: CMP-MEMORY
atlas_type: Component
atlas_name: Memory
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 36
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
consumes:
- '[[Interfaces & Contracts/CON-MEMORY-UPDATE-REQUEST — MemoryUpdateRequest|CON-MEMORY-UPDATE-REQUEST
  · MemoryUpdateRequest]]'
- '[[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT
  · PostMortemOutput]]'
- '[[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT
  · VerifierResult]]'
- '[[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY
  · Evidence, Memory & Retrieval]]'
part_of_from:
- '[[Components/CMP-MEM-EPISODIC — Episodic Memory|CMP-MEM-EPISODIC · Episodic Memory]]'
- '[[Components/CMP-MEM-FACTS — Semantic Facts|CMP-MEM-FACTS · Semantic Facts]]'
- '[[Components/CMP-MEM-HYPOTHESES — Hypotheses|CMP-MEM-HYPOTHESES · Hypotheses]]'
- '[[Components/CMP-MEM-STRATEGY — Strategy - Experiment Memory|CMP-MEM-STRATEGY ·
  Strategy / Experiment Memory]]'
- '[[Components/CMP-MEM-TOPOLOGY — Topological Memory|CMP-MEM-TOPOLOGY · Topological
  Memory]]'
- '[[Components/CMP-SKILL-COMPETENCE — Skill Competence Registry|CMP-SKILL-COMPETENCE
  · Skill Competence Registry]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-MEMORY — Canonical Memory|EVID-48-CANON-MEMORY · Canonical
  Memory]]'
- '[[Evidence/EVID-48-MEMORY — Memory — baseline inspection|EVID-48-MEMORY · Memory
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

# CMP-MEMORY — Memory

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

SQLite observations, actions, skill results, facts, topology and strategies exist. Full canonical retrieval, consolidation and activation lifecycle remain incomplete. Memory is outside Cortex.

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical child: [[Components/CMP-MEM-EPISODIC — Episodic Memory|CMP-MEM-EPISODIC · Episodic Memory]]
- Technical child: [[Components/CMP-MEM-FACTS — Semantic Facts|CMP-MEM-FACTS · Semantic Facts]]
- Technical child: [[Components/CMP-MEM-HYPOTHESES — Hypotheses|CMP-MEM-HYPOTHESES · Hypotheses]]
- Technical child: [[Components/CMP-MEM-STRATEGY — Strategy - Experiment Memory|CMP-MEM-STRATEGY · Strategy / Experiment Memory]]
- Technical child: [[Components/CMP-MEM-TOPOLOGY — Topological Memory|CMP-MEM-TOPOLOGY · Topological Memory]]
- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- Technical child: [[Components/CMP-SKILL-COMPETENCE — Skill Competence Registry|CMP-SKILL-COMPETENCE · Skill Competence Registry]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY · Evidence, Memory & Retrieval]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Input: [[Interfaces & Contracts/CON-MEMORY-UPDATE-REQUEST — MemoryUpdateRequest|CON-MEMORY-UPDATE-REQUEST · MemoryUpdateRequest]]
- Input: [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- Input: [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- Input: [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]

## Interfaces and contracts

- Input: [[Interfaces & Contracts/CON-MEMORY-UPDATE-REQUEST — MemoryUpdateRequest|CON-MEMORY-UPDATE-REQUEST · MemoryUpdateRequest]]
- Input: [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- Input: [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]

## Data artifacts

- Input: [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-CANON-MEMORY — Canonical Memory|EVID-48-CANON-MEMORY · Canonical Memory]]
- Supporting: [[Evidence/EVID-48-MEMORY — Memory — baseline inspection|EVID-48-MEMORY · Memory — baseline inspection]]

## Research questions

None mapped.

## Research threads

None mapped.

## Papers

None mapped.

## Findings and contradictions

None mapped.

## Decisions

None mapped.

## Experiment leads

None mapped.

## History

None mapped.

Outgoing/incoming edges show supersedes / superseded by and decomposed into / from.

## Review / proposals

No accepted proposal is mapped unless represented by the Registry decisions above. Keep authored proposals in separate notes; accepted changes must enter through Registry review. Generated notes do not accept changes or claims.

[[Home/Research Atlas|Research Atlas Home]]
