---
atlas_id: CMP-INPUT-EXECUTOR
atlas_type: Component
atlas_name: InputExecutor
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 49
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
consumes:
- '[[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION
  · Primitive Action Vocabulary]]'
controls:
- '[[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE
  · Game / Environment]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY ·
  Action & Safety]]'
supplies:
- '[[Data Artifacts/DAT-ACTION-RESULT — ActionResult|DAT-ACTION-RESULT · ActionResult]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]'
- '[[Evidence/EVID-48-INPUT — Input — baseline inspection|EVID-48-INPUT · Input —
  baseline inspection]]'
- '[[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER
  · Skill Runner — baseline inspection]]'
- '[[Evidence/EVID-48-TASK-EXECUTOR — Task Executor — baseline inspection|EVID-48-TASK-EXECUTOR
  · Task Executor — baseline inspection]]'
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

# CMP-INPUT-EXECUTOR — InputExecutor

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Separate primitive-input boundary enforcing target focus, rate limit and emergency stop. Active-task checks and action masks belong to Manager execution composition; transition logging is supplied when configured. This class alone does not establish all canonical input preconditions.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY · Action & Safety]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Input: [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- Output: [[Data Artifacts/DAT-ACTION-RESULT — ActionResult|DAT-ACTION-RESULT · ActionResult]]

## Interfaces and contracts

- Input: [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]

## Data artifacts

- Output: [[Data Artifacts/DAT-ACTION-RESULT — ActionResult|DAT-ACTION-RESULT · ActionResult]]

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]
- Supporting: [[Evidence/EVID-48-INPUT — Input — baseline inspection|EVID-48-INPUT · Input — baseline inspection]]
- Supporting: [[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER · Skill Runner — baseline inspection]]
- Supporting: [[Evidence/EVID-48-TASK-EXECUTOR — Task Executor — baseline inspection|EVID-48-TASK-EXECUTOR · Task Executor — baseline inspection]]

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
