---
atlas_id: CMP-MANAGER-GROUNDING
atlas_type: Component
atlas_name: Grounding
atlas_level: L3
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: expansion
overview_order: 43
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
grounds:
- '[[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT
  · TaskSpec / bounded Skill Contract]]'
part_of:
- '[[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-EXECUTIVE — Executive Control & Contracts|DOM-EXECUTIVE
  · Executive Control & Contracts]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-EXECUTIVE — Canonical Executive|EVID-48-CANON-EXECUTIVE
  · Canonical Executive]]'
- '[[Evidence/EVID-48-GROUNDING — Grounding — baseline inspection|EVID-48-GROUNDING
  · Grounding — baseline inspection]]'
- '[[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION
  · Submission — baseline inspection]]'
- '[[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING
  · Test Grounding — baseline inspection]]'
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

# CMP-MANAGER-GROUNDING — Grounding

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Canonical Manager grounding responsibility implemented by bounded visible-candidate selection and grounded Cortex submission; ambiguous or unsupported targets fail closed.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Research mapping: unmapped. Research direction: None.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Technical structure

- Technical parent: [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]

Technical parents are outgoing `part_of`; children are incoming `part_of`.

## Presentation

- Presentation Domain: [[Architecture/Domains/DOM-EXECUTIVE — Executive Control & Contracts|DOM-EXECUTIVE · Executive Control & Contracts]]

L-level: L3. Overview visibility: expansion.

## Inputs and outputs

None mapped.

## Interfaces and contracts

- grounds: [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]

## Data artifacts

None mapped.

## Measurement points

None mapped.

## Evidence

- Supporting: [[Evidence/EVID-48-CANON-EXECUTIVE — Canonical Executive|EVID-48-CANON-EXECUTIVE · Canonical Executive]]
- Supporting: [[Evidence/EVID-48-GROUNDING — Grounding — baseline inspection|EVID-48-GROUNDING · Grounding — baseline inspection]]
- Supporting: [[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION · Submission — baseline inspection]]
- Supporting: [[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING · Test Grounding — baseline inspection]]

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
