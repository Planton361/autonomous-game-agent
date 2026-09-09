---
atlas_id: CMP-REPLAY-BUFFER
atlas_type: Component
atlas_name: Replay Buffer
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 56
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: partial
verification_status: unverified
consumes:
- '[[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT
  · VerifierResult]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN
  · Verification & Learning]]'
supplies:
- '[[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION
  · ReplayTransition]]'
supports_from: &id001
- '[[Evidence/EVID-48-CANON-VERIFY — Canonical Verify|EVID-48-CANON-VERIFY · Canonical
  Verify]]'
- '[[Evidence/EVID-48-REPLAY — Replay — baseline inspection|EVID-48-REPLAY · Replay
  — baseline inspection]]'
- '[[Evidence/EVID-48-TEST-REPLAY — Test Replay — baseline inspection|EVID-48-TEST-REPLAY
  · Test Replay — baseline inspection]]'
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

# CMP-REPLAY-BUFFER — Replay Buffer

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Fixed-capacity FIFO and seeded sampling exist for synthetic ReplayTransition objects. Complete admissible run/contract/verifier provenance and official training eligibility are not enforced by this buffer.

## Classification

Architecture authority: canonical-target. Implementation: partial. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]] — `consumes` → [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]] — `presented_in_domain` → [[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN · Verification & Learning]]
- [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]] — `supplies` → [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]
- [[Evidence/EVID-48-CANON-VERIFY — Canonical Verify|EVID-48-CANON-VERIFY · Canonical Verify]] — `supports` → [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]]
- [[Evidence/EVID-48-REPLAY — Replay — baseline inspection|EVID-48-REPLAY · Replay — baseline inspection]] — `supports` → [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]]
- [[Evidence/EVID-48-TEST-REPLAY — Test Replay — baseline inspection|EVID-48-TEST-REPLAY · Test Replay — baseline inspection]] — `supports` → [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]]

[[Home/Research Atlas|Research Atlas Home]]
