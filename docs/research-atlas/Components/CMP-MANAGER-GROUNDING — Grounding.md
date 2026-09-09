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
supports_from: &id001
- '[[Evidence/EVID-48-CANON-EXECUTIVE — Canonical Executive|EVID-48-CANON-EXECUTIVE
  · Canonical Executive]]'
- '[[Evidence/EVID-48-GROUNDING — Grounding — baseline inspection|EVID-48-GROUNDING
  · Grounding — baseline inspection]]'
- '[[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION
  · Submission — baseline inspection]]'
- '[[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING
  · Test Grounding — baseline inspection]]'
presented_in_domain: []
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

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]] — `grounds` → [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]] — `part_of` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-48-CANON-EXECUTIVE — Canonical Executive|EVID-48-CANON-EXECUTIVE · Canonical Executive]] — `supports` → [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]
- [[Evidence/EVID-48-GROUNDING — Grounding — baseline inspection|EVID-48-GROUNDING · Grounding — baseline inspection]] — `supports` → [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]
- [[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION · Submission — baseline inspection]] — `supports` → [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]
- [[Evidence/EVID-48-TEST-GROUNDING — Test Grounding — baseline inspection|EVID-48-TEST-GROUNDING · Test Grounding — baseline inspection]] — `supports` → [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]

[[Home/Research Atlas|Research Atlas Home]]
