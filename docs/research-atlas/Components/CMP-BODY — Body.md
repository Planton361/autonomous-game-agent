---
atlas_id: CMP-BODY
atlas_type: Component
atlas_name: Body
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 45
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
executes:
- '[[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT
  · TaskSpec / bounded Skill Contract]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY ·
  Action & Safety]]'
supplies:
- '[[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION
  · Primitive Action Vocabulary]]'
constrains_from:
- '[[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT
  · TaskSpec / bounded Skill Contract]]'
controls_from:
- '[[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]'
part_of_from:
- '[[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]'
supports_from: &id001
- '[[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline
  inspection]]'
- '[[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]'
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

# CMP-BODY — Body

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Reusable heuristic skills propose one primitive at a time from visible grounded targets; ManagerTaskExecutor binds execution to an active task and SkillRunner enforces the skill action mask. Learned Body and full canonical skill breadth are not claimed.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- Technical child: [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY · Action & Safety]]

L-level: L2. Overview visibility: main.

## Inputs and outputs

- Output: [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]

## Interfaces and contracts

- Constrained by: [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- executes: [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- Output: [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]

## Data artifacts

None mapped.

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline inspection]]
- Supporting: [[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]
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
