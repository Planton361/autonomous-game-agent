---
atlas_id: FUNC-ACQUIRE
atlas_type: Function
atlas_name: Acquire
atlas_level: null
atlas_generated: true
registry_schema_version: '0.3'
overview_visibility: null
overview_order: null
research_mapping: unmapped
research_direction: null
contributes_to_function_from:
- '[[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]]'
- '[[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE
  · Optional Visible-State Bridge]]'
- '[[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE
  · Game / Environment]]'
supports_from: &id001
- '[[Evidence/EVID-FUNCTION-SEMANTICS-137 — Accepted Function semantics (-137)|EVID-FUNCTION-SEMANTICS-137
  · Accepted Function semantics (#137)]]'
part_of: []
presented_in_domain: []
measured_at: []
studied_by: []
supersedes: []
supersedes_from: []
decomposed_into: []
decomposed_into_from: []
contradicts: []
contributes_to_function: []
supported_by: *id001
contradicted_by: []
research_questions: []
research_components: []
research_interfaces: []
research_threads: []
---

# FUNC-ACQUIRE — Acquire

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Visible-state acquisition and ingress context. The Environment remains external to the Agent.

## Functional participants

Membership records participation only; it does not imply authority or technical containment.

- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]]
- [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]]
- [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]

Only an explicit functional order expresses order. Otherwise, list order is deterministic presentation and has no functional meaning.

## Registry relationships

- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]] — `contributes_to_function` → [[Functions/FUNC-ACQUIRE — Acquire|FUNC-ACQUIRE · Acquire]]
- [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]] — `contributes_to_function` → [[Functions/FUNC-ACQUIRE — Acquire|FUNC-ACQUIRE · Acquire]]
- [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]] — `contributes_to_function` → [[Functions/FUNC-ACQUIRE — Acquire|FUNC-ACQUIRE · Acquire]]
- [[Evidence/EVID-FUNCTION-SEMANTICS-137 — Accepted Function semantics (-137)|EVID-FUNCTION-SEMANTICS-137 · Accepted Function semantics (#137)]] — `supports` → [[Functions/FUNC-ACQUIRE — Acquire|FUNC-ACQUIRE · Acquire]]

[[Home/Research Atlas|Research Atlas Home]]
