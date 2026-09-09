---
atlas_id: CMP-MANAGER
atlas_type: Component
atlas_name: Manager
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 11
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: integration-tested
consumes:
- '[[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT
  · PlannerOutput]]'
- '[[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT
  · VerifierResult]]'
- '[[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER
  · Cortex to Manager]]'
controls:
- '[[Components/CMP-BODY — Body|CMP-BODY · Body]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-EXECUTIVE — Executive Control & Contracts|DOM-EXECUTIVE
  · Executive Control & Contracts]]'
related_to_research_question: &id002
- '[[Research Questions/RQ-PROGRAM-AB-001 — Program A–B working question|RQ-PROGRAM-AB-001
  · Program A–B working question]]'
supplies:
- '[[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT
  · TaskSpec / bounded Skill Contract]]'
measured_at_from:
- '[[Measurements/MEAS-MANAGER-DISPOSITION-001 — Manager disposition and TaskSpec|MEAS-MANAGER-DISPOSITION-001
  · Manager disposition and TaskSpec]]'
part_of_from:
- '[[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]'
- '[[Components/CMP-MANAGER-SCHED-COMP — Scheduling and Completion|CMP-MANAGER-SCHED-COMP
  · Scheduling and Completion]]'
proposes_to_from:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
supports_from: &id001
- '[[Decisions/DEC-ATLAS-PILOT-001 — Approved Atlas pilot scope|DEC-ATLAS-PILOT-001
  · Approved Atlas pilot scope]]'
- '[[Evidence/EVID-48-MANAGER — Manager — baseline inspection|EVID-48-MANAGER · Manager
  — baseline inspection]]'
- '[[Evidence/EVID-48-SCHEDULING — Scheduling — baseline inspection|EVID-48-SCHEDULING
  · Scheduling — baseline inspection]]'
- '[[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION
  · Submission — baseline inspection]]'
- '[[Evidence/EVID-48-TASK-EXECUTOR — Task Executor — baseline inspection|EVID-48-TASK-EXECUTOR
  · Task Executor — baseline inspection]]'
- '[[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING
  · Test Grounding — baseline inspection]]'
- '[[Evidence/EVID-CANON-MANAGER — EVID-CANON-MANAGER|EVID-CANON-MANAGER · EVID-CANON-MANAGER]]'
- '[[Evidence/EVID-GH-MANAGER-GROUND — EVID-GH-MANAGER-GROUND|EVID-GH-MANAGER-GROUND
  · EVID-GH-MANAGER-GROUND]]'
- '[[Evidence/EVID-GH-MANAGER-INTEGRATION — EVID-GH-MANAGER-INTEGRATION|EVID-GH-MANAGER-INTEGRATION
  · EVID-GH-MANAGER-INTEGRATION]]'
- '[[Evidence/EVID-GH-MANAGER-ORCHESTRATOR — EVID-GH-MANAGER-ORCHESTRATOR|EVID-GH-MANAGER-ORCHESTRATOR
  · EVID-GH-MANAGER-ORCHESTRATOR]]'
- '[[Evidence/EVID-GH-MANAGER-SCHEDULING-TEST — Manager scheduling checks|EVID-GH-MANAGER-SCHEDULING-TEST
  · Manager scheduling checks]]'
- '[[Evidence/EVID-GH-MANAGER-SPEC — EVID-GH-MANAGER-SPEC|EVID-GH-MANAGER-SPEC · EVID-GH-MANAGER-SPEC]]'
- '[[Evidence/EVID-GH-MANAGER-TASK — EVID-GH-MANAGER-TASK|EVID-GH-MANAGER-TASK · EVID-GH-MANAGER-TASK]]'
- '[[Evidence/EVID-GH-MANAGER-TEST — EVID-GH-MANAGER-TEST|EVID-GH-MANAGER-TEST · EVID-GH-MANAGER-TEST]]'
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

# CMP-MANAGER — Manager

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Authority boundary for validating proposals, grounding visible targets, constructing bounded task contracts, scheduling and closing them using verified outcomes. TaskSpec is a Contract.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: integration-tested.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- Technical child: [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]
- Technical child: [[Components/CMP-MANAGER-SCHED-COMP — Scheduling and Completion|CMP-MANAGER-SCHED-COMP · Scheduling and Completion]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-EXECUTIVE — Executive Control & Contracts|DOM-EXECUTIVE · Executive Control & Contracts]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Input: [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- Input: [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- Input: [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]
- Output: [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]

## Interfaces and contracts

- Input: [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- Input: [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- Input: [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]
- Output: [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]

## Data artifacts

None mapped.

## Measurement points

- Measurement point: [[Measurements/MEAS-MANAGER-DISPOSITION-001 — Manager disposition and TaskSpec|MEAS-MANAGER-DISPOSITION-001 · Manager disposition and TaskSpec]]

## Evidence

- Supporting: [[Evidence/EVID-48-MANAGER — Manager — baseline inspection|EVID-48-MANAGER · Manager — baseline inspection]]
- Supporting: [[Evidence/EVID-48-SCHEDULING — Scheduling — baseline inspection|EVID-48-SCHEDULING · Scheduling — baseline inspection]]
- Supporting: [[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION · Submission — baseline inspection]]
- Supporting: [[Evidence/EVID-48-TASK-EXECUTOR — Task Executor — baseline inspection|EVID-48-TASK-EXECUTOR · Task Executor — baseline inspection]]
- Supporting: [[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING · Test Grounding — baseline inspection]]
- Supporting: [[Evidence/EVID-CANON-MANAGER — EVID-CANON-MANAGER|EVID-CANON-MANAGER · EVID-CANON-MANAGER]]
- Supporting: [[Evidence/EVID-GH-MANAGER-GROUND — EVID-GH-MANAGER-GROUND|EVID-GH-MANAGER-GROUND · EVID-GH-MANAGER-GROUND]]
- Supporting: [[Evidence/EVID-GH-MANAGER-INTEGRATION — EVID-GH-MANAGER-INTEGRATION|EVID-GH-MANAGER-INTEGRATION · EVID-GH-MANAGER-INTEGRATION]]
- Supporting: [[Evidence/EVID-GH-MANAGER-ORCHESTRATOR — EVID-GH-MANAGER-ORCHESTRATOR|EVID-GH-MANAGER-ORCHESTRATOR · EVID-GH-MANAGER-ORCHESTRATOR]]
- Supporting: [[Evidence/EVID-GH-MANAGER-SCHEDULING-TEST — Manager scheduling checks|EVID-GH-MANAGER-SCHEDULING-TEST · Manager scheduling checks]]
- Supporting: [[Evidence/EVID-GH-MANAGER-SPEC — EVID-GH-MANAGER-SPEC|EVID-GH-MANAGER-SPEC · EVID-GH-MANAGER-SPEC]]
- Supporting: [[Evidence/EVID-GH-MANAGER-TASK — EVID-GH-MANAGER-TASK|EVID-GH-MANAGER-TASK · EVID-GH-MANAGER-TASK]]
- Supporting: [[Evidence/EVID-GH-MANAGER-TEST — EVID-GH-MANAGER-TEST|EVID-GH-MANAGER-TEST · EVID-GH-MANAGER-TEST]]

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
