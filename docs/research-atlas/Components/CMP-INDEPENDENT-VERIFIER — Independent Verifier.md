---
atlas_id: CMP-INDEPENDENT-VERIFIER
atlas_type: Component
atlas_name: Independent Verifier
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 52
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
consumes:
- '[[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]'
observes:
- '[[Data Artifacts/DAT-VISIBLE-OUTCOME — Visible Outcome|DAT-VISIBLE-OUTCOME · Visible
  Outcome]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN
  · Verification & Learning]]'
supplies:
- '[[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT
  · VerifierResult]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-VERIFY — Canonical Verify|EVID-48-CANON-VERIFY · Canonical
  Verify]]'
- '[[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER
  · Skill Runner — baseline inspection]]'
- '[[Evidence/EVID-48-VERIFIER — Verifier — baseline inspection|EVID-48-VERIFIER ·
  Verifier — baseline inspection]]'
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

# CMP-INDEPENDENT-VERIFIER — Independent Verifier

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Deterministic reach-target, dialogue and interaction outcome evaluators return canonical VerifierResult. Independent of Cortex reflection; screenshot change alone is not success.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]] — `consumes` → [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]] — `observes` → [[Data Artifacts/DAT-VISIBLE-OUTCOME — Visible Outcome|DAT-VISIBLE-OUTCOME · Visible Outcome]]
- [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]] — `presented_in_domain` → [[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN · Verification & Learning]]
- [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]] — `supplies` → [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- [[Evidence/EVID-48-CANON-VERIFY — Canonical Verify|EVID-48-CANON-VERIFY · Canonical Verify]] — `supports` → [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]]
- [[Evidence/EVID-48-SKILL-RUNNER — Skill Runner — baseline inspection|EVID-48-SKILL-RUNNER · Skill Runner — baseline inspection]] — `supports` → [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]]
- [[Evidence/EVID-48-VERIFIER — Verifier — baseline inspection|EVID-48-VERIFIER · Verifier — baseline inspection]] — `supports` → [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]]

[[Home/Research Atlas|Research Atlas Home]]
