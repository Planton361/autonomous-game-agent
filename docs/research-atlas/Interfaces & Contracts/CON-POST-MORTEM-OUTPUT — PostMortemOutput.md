---
atlas_id: CON-POST-MORTEM-OUTPUT
atlas_type: Contract
atlas_name: PostMortemOutput
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 55
research_mapping: unmapped
research_direction: null
architecture_authority: implementation-derived
implementation_status: implemented
verification_status: unverified
consumes_from:
- '[[Components/CMP-MEMORY — Memory|CMP-MEMORY · Memory]]'
supplies_from:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
supports_from: &id001
- '[[Evidence/EVID-48-POST-MORTEM — Post Mortem — baseline inspection|EVID-48-POST-MORTEM
  · Post Mortem — baseline inspection]]'
- '[[Evidence/EVID-48-REFLECTION — Reflection — baseline inspection|EVID-48-REFLECTION
  · Reflection — baseline inspection]]'
part_of: []
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

# CON-POST-MORTEM-OUTPUT — PostMortemOutput

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Cortex reflection/post-verification contract: observed outcome, typed notes, hypotheses and proposed memory updates. Not part of independent Verifier authority or an automatic memory writer.

## Classification

Architecture authority: implementation-derived. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-MEMORY — Memory|CMP-MEMORY · Memory]] — `consumes` → [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]] — `supplies` → [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- [[Evidence/EVID-48-POST-MORTEM — Post Mortem — baseline inspection|EVID-48-POST-MORTEM · Post Mortem — baseline inspection]] — `supports` → [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- [[Evidence/EVID-48-REFLECTION — Reflection — baseline inspection|EVID-48-REFLECTION · Reflection — baseline inspection]] — `supports` → [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]

[[Home/Research Atlas|Research Atlas Home]]
