---
atlas_id: EVID-48-SUBMISSION
atlas_type: Evidence
atlas_name: Submission — baseline inspection
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
path: src/fh_agent/manager/grounded_cortex_submission.py
symbol: GroundedCortexTaskSubmitter.plan_ground_and_submit
line: 43
supports:
- '[[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]'
- '[[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]'
- '[[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER
  · Cortex to Manager]]'
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

# EVID-48-SUBMISSION — Submission — baseline inspection

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

GroundedCortexTaskSubmitter.plan_ground_and_submit requests Cortex output, builds the grounding request from current visible evidence, obtains grounding and submits to ManagerOrchestrator. It does not run Body or send input.

## Evidence locator

Provenance: github_implementation. Checked: 2026-09-09.

[Source](https://github.com/Planton361/autonomous-game-agent/blob/7b4ec2e1497dec50c94b921b61dab42245bf5c90/src/fh_agent/manager/grounded_cortex_submission.py#L43) · GroundedCortexTaskSubmitter.plan_ground_and_submit

## Registry relationships

- [[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION · Submission — baseline inspection]] — `supports` → [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION · Submission — baseline inspection]] — `supports` → [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]
- [[Evidence/EVID-48-SUBMISSION — Submission — baseline inspection|EVID-48-SUBMISSION · Submission — baseline inspection]] — `supports` → [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]

[[Home/Research Atlas|Research Atlas Home]]
