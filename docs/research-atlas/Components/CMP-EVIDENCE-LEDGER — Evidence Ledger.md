---
atlas_id: CMP-EVIDENCE-LEDGER
atlas_type: Component
atlas_name: Evidence Ledger
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 35
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
consumes:
- '[[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY
  · Evidence, Memory & Retrieval]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-MEMORY — Canonical Memory|EVID-48-CANON-MEMORY · Canonical
  Memory]]'
- '[[Evidence/EVID-48-EVENTS — Events — baseline inspection|EVID-48-EVENTS · Events
  — baseline inspection]]'
- '[[Evidence/EVID-48-EVIDENCE — Evidence — baseline inspection|EVID-48-EVIDENCE ·
  Evidence — baseline inspection]]'
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

# CMP-EVIDENCE-LEDGER — Evidence Ledger

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Screenshot evidence records retain hashes and dimensions; append-only event logging links actions and verifier outcomes. Complete immutable lifecycle/provenance enforcement is not established by these stores alone.

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence Ledger]] — `consumes` → [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]
- [[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence Ledger]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence Ledger]] — `presented_in_domain` → [[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY · Evidence, Memory & Retrieval]]
- [[Evidence/EVID-48-CANON-MEMORY — Canonical Memory|EVID-48-CANON-MEMORY · Canonical Memory]] — `supports` → [[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence Ledger]]
- [[Evidence/EVID-48-EVENTS — Events — baseline inspection|EVID-48-EVENTS · Events — baseline inspection]] — `supports` → [[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence Ledger]]
- [[Evidence/EVID-48-EVIDENCE — Evidence — baseline inspection|EVID-48-EVIDENCE · Evidence — baseline inspection]] — `supports` → [[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence Ledger]]

[[Home/Research Atlas|Research Atlas Home]]
