---
atlas_id: EVID-48-UI
atlas_type: Evidence
atlas_name: Ui — baseline inspection
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
path: src/fh_agent/perception/ui_state.py
symbol: classify_ui_state
line: 15
supports:
- '[[Components/CMP-PERCEPTION-UI-STATE — UI State Classification|CMP-PERCEPTION-UI-STATE
  · UI State Classification]]'
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

# EVID-48-UI — Ui — baseline inspection

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Source inspection at the accepted baseline. classify_ui_state implements deterministic classification from sanitized visible UI fields and OCR spans; unknown when insufficient. This is a code-derived responsibility used by ObservationBuilder, not a validated pixel classifier.

## Evidence locator

Provenance: github_implementation. Checked: 2026-09-09.

[Source](https://github.com/Planton361/autonomous-game-agent/blob/7b4ec2e1497dec50c94b921b61dab42245bf5c90/src/fh_agent/perception/ui_state.py#L15) · classify_ui_state

## Registry relationships

- [[Evidence/EVID-48-UI — Ui — baseline inspection|EVID-48-UI · Ui — baseline inspection]] — `supports` → [[Components/CMP-PERCEPTION-UI-STATE — UI State Classification|CMP-PERCEPTION-UI-STATE · UI State Classification]]

[[Home/Research Atlas|Research Atlas Home]]
