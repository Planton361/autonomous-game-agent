---
atlas_id: EVID-48-BODY
atlas_type: Evidence
atlas_name: Body — baseline inspection
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
path: src/fh_agent/body/skills/basic_reach_target.py
symbol: BasicReachTargetSkill.next_action
line: 48
supports:
- '[[Components/CMP-BODY — Body|CMP-BODY · Body]]'
- '[[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]'
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

# EVID-48-BODY — Body — baseline inspection

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

BasicReachTargetSkill.next_action proposes a single primitive from a visible grounded target, otherwise wait. It is a reusable heuristic Body path, not a separate Manager-declared Reflex implementation. No executable Reflex path was found in baseline source inspection.

## Evidence locator

Provenance: github_implementation. Checked: 2026-09-09.

[Source](https://github.com/Planton361/autonomous-game-agent/blob/7b4ec2e1497dec50c94b921b61dab42245bf5c90/src/fh_agent/body/skills/basic_reach_target.py#L48) · BasicReachTargetSkill.next_action

## Registry relationships

- [[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline inspection]] — `supports` → [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Evidence/EVID-48-BODY — Body — baseline inspection|EVID-48-BODY · Body — baseline inspection]] — `supports` → [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]

[[Home/Research Atlas|Research Atlas Home]]
