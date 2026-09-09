---
atlas_id: EVID-48-VERIFIER-RESULT
atlas_type: Evidence
atlas_name: Verifier Result — baseline inspection
atlas_level: null
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: null
overview_order: null
research_mapping: unmapped
research_direction: null
provenance_kind: github_implementation
checked_date: '2026-09-09'
repository: Planton361/autonomous-game-agent
ref: 7b4ec2e1497dec50c94b921b61dab42245bf5c90
path: src/fh_agent/verifier/schemas.py
symbol: VerifierResult
line: 35
supports:
- '[[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT
  · VerifierResult]]'
- '[[Data Artifacts/DAT-VISIBLE-OUTCOME — Visible Outcome|DAT-VISIBLE-OUTCOME · Visible
  Outcome]]'
part_of: []
presented_in_domain: []
measured_at: []
studied_by: []
supersedes: []
supersedes_from: []
decomposed_into: []
decomposed_into_from: []
contradicts: []
supported_by: []
contradicted_by: []
research_questions: []
research_components: []
research_interfaces: []
research_threads: []
---

# EVID-48-VERIFIER-RESULT — Verifier Result — baseline inspection

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

VerifierResult is a frozen outcome payload with success/progress/failure/abstain, failure kind and evidence IDs; validation requires failure_kind exactly for failure. It labels outcomes after evaluation and is not a first-class pre-verification VisibleOutcome artifact.

## Evidence locator

Provenance: github_implementation. Checked: 2026-09-09.

[Source](https://github.com/Planton361/autonomous-game-agent/blob/7b4ec2e1497dec50c94b921b61dab42245bf5c90/src/fh_agent/verifier/schemas.py#L35) · VerifierResult

## Registry relationships

- [[Evidence/EVID-48-VERIFIER-RESULT — Verifier Result — baseline inspection|EVID-48-VERIFIER-RESULT · Verifier Result — baseline inspection]] — `supports` → [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- [[Evidence/EVID-48-VERIFIER-RESULT — Verifier Result — baseline inspection|EVID-48-VERIFIER-RESULT · Verifier Result — baseline inspection]] — `supports` → [[Data Artifacts/DAT-VISIBLE-OUTCOME — Visible Outcome|DAT-VISIBLE-OUTCOME · Visible Outcome]]

[[Home/Research Atlas|Research Atlas Home]]
