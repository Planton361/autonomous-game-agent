---
atlas_id: EVID-48-CONTEXT
atlas_type: Evidence
atlas_name: Context — baseline inspection
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
path: src/fh_agent/planner/context.py
symbol: build_plan_context
line: 71
supports:
- '[[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]'
- '[[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]'
- '[[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT
  · CortexContext]]'
- '[[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT
  · Bounded retrieval snapshot (target only)]]'
- '[[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory
  to Cortex]]'
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

# EVID-48-CONTEXT — Context — baseline inspection

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

build_plan_context consumes a caller-supplied memory_summary and constructs CortexContext from visible observation, facts, hypotheses, prior skill outcomes and constraints. It does not retrieve memory or create a versioned RetrievalSnapshot. The memory-to-Cortex path therefore remains partial.

## Evidence locator

Provenance: github_implementation. Checked: 2026-09-09.

[Source](https://github.com/Planton361/autonomous-game-agent/blob/7b4ec2e1497dec50c94b921b61dab42245bf5c90/src/fh_agent/planner/context.py#L71) · build_plan_context

## Registry relationships

- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT · Bounded retrieval snapshot (target only)]]
- [[Evidence/EVID-48-CONTEXT — Context — baseline inspection|EVID-48-CONTEXT · Context — baseline inspection]] — `supports` → [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]

[[Home/Research Atlas|Research Atlas Home]]
