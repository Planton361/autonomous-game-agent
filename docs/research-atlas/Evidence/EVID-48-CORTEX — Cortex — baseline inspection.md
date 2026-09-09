---
atlas_id: EVID-48-CORTEX
atlas_type: Evidence
atlas_name: Cortex — baseline inspection
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
path: src/fh_agent/planner/cortex.py
symbol: Cortex.plan_next_goal
line: 30
supports:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
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

# EVID-48-CORTEX — Cortex — baseline inspection

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Cortex.plan_next_goal builds context, invokes the supplied LLM client, parses PlannerOutput, checks evidence scope and rejects unavailable skills. It returns a proposal without primitive execution; the Manager submission boundary is separate.

## Evidence locator

Provenance: github_implementation. Checked: 2026-09-09.

[Source](https://github.com/Planton361/autonomous-game-agent/blob/7b4ec2e1497dec50c94b921b61dab42245bf5c90/src/fh_agent/planner/cortex.py#L30) · Cortex.plan_next_goal

## Registry relationships

- [[Evidence/EVID-48-CORTEX — Cortex — baseline inspection|EVID-48-CORTEX · Cortex — baseline inspection]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-48-CORTEX — Cortex — baseline inspection|EVID-48-CORTEX · Cortex — baseline inspection]] — `supports` → [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]

[[Home/Research Atlas|Research Atlas Home]]
