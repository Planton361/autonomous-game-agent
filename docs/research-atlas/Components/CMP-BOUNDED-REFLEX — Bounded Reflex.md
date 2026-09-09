---
atlas_id: CMP-BOUNDED-REFLEX
atlas_type: Component
atlas_name: Bounded Reflex
atlas_level: L3
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: expansion
overview_order: 46
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: target-only
verification_status: unverified
part_of:
- '[[Components/CMP-BODY — Body|CMP-BODY · Body]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY ·
  Action & Safety]]'
supplies:
- '[[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION
  · Primitive Action Vocabulary]]'
constrains_from:
- '[[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT
  · TaskSpec / bounded Skill Contract]]'
supports_from: &id001
- '[[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline
  inspection]]'
- '[[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]'
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

# CMP-BOUNDED-REFLEX — Bounded Reflex

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Canonical fast Body path restricted to Manager-declared triggers and contract permissions. No separate current executable reflex path was found; ordinary heuristic action selection is not relabeled Reflex.

## Classification

Architecture authority: canonical-target. Implementation: target-only. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Components/CMP-BODY — Body|CMP-BODY · Body]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY · Action & Safety]]

L-level: L3. Overview visibility: expansion.

## Inputs and outputs

- Output: [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]

## Interfaces and contracts

- Constrained by: [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- Output: [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]

## Data artifacts

None mapped.

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline inspection]]
- Supporting: [[Evidence/EVID-48-CANON-BODY — Canonical Body|EVID-48-CANON-BODY · Canonical Body]]

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
