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

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `consumes` → [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `consumes` → [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `consumes` → [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `controls` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Measurements/MEAS-MANAGER-DISPOSITION-001 — Manager disposition and TaskSpec|MEAS-MANAGER-DISPOSITION-001 · Manager disposition and TaskSpec]] — `measured_at` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]] — `part_of` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Components/CMP-MANAGER-SCHED-COMP — Scheduling and Completion|CMP-MANAGER-SCHED-COMP · Scheduling and Completion]] — `part_of` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `presented_in_domain` → [[Architecture/Domains/DOM-EXECUTIVE — Executive Control & Contracts|DOM-EXECUTIVE · Executive Control & Contracts]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `proposes_to` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `related_to_research_question` → [[Research Questions/RQ-PROGRAM-AB-001 — Program A–B working question|RQ-PROGRAM-AB-001 · Program A–B working question]]
- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]] — `supplies` → [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- [[Decisions/DEC-ATLAS-PILOT-001 — Approved Atlas pilot scope|DEC-ATLAS-PILOT-001 · Approved Atlas pilot scope]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-48-MANAGER — Manager — baseline inspection|EVID-48-MANAGER · Manager — baseline inspection]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-48-SCHEDULING — Scheduling — baseline inspection|EVID-48-SCHEDULING · Scheduling — baseline inspection]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION · Submission — baseline inspection]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-48-TASK-EXECUTOR — Task Executor — baseline inspection|EVID-48-TASK-EXECUTOR · Task Executor — baseline inspection]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING · Test Grounding — baseline inspection]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-CANON-MANAGER — EVID-CANON-MANAGER|EVID-CANON-MANAGER · EVID-CANON-MANAGER]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-GH-MANAGER-GROUND — EVID-GH-MANAGER-GROUND|EVID-GH-MANAGER-GROUND · EVID-GH-MANAGER-GROUND]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-GH-MANAGER-INTEGRATION — EVID-GH-MANAGER-INTEGRATION|EVID-GH-MANAGER-INTEGRATION · EVID-GH-MANAGER-INTEGRATION]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-GH-MANAGER-ORCHESTRATOR — EVID-GH-MANAGER-ORCHESTRATOR|EVID-GH-MANAGER-ORCHESTRATOR · EVID-GH-MANAGER-ORCHESTRATOR]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-GH-MANAGER-SCHEDULING-TEST — Manager scheduling checks|EVID-GH-MANAGER-SCHEDULING-TEST · Manager scheduling checks]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-GH-MANAGER-SPEC — EVID-GH-MANAGER-SPEC|EVID-GH-MANAGER-SPEC · EVID-GH-MANAGER-SPEC]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-GH-MANAGER-TASK — EVID-GH-MANAGER-TASK|EVID-GH-MANAGER-TASK · EVID-GH-MANAGER-TASK]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-GH-MANAGER-TEST — EVID-GH-MANAGER-TEST|EVID-GH-MANAGER-TEST · EVID-GH-MANAGER-TEST]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]

## Research threads

- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

[[Home/Research Atlas|Research Atlas Home]]
