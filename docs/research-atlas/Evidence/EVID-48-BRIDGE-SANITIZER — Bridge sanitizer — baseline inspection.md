---
atlas_id: EVID-48-BRIDGE-SANITIZER
atlas_type: Evidence
atlas_name: Bridge sanitizer — baseline inspection
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
path: src/fh_agent/bridge/sanitizer.py
symbol: sanitize_bridge_payload
line: 173
supports:
- '[[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|CMP-NO-SPOILER-FIREWALL
  · No-Spoiler Firewall]]'
- '[[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE
  · Optional Visible-State Bridge]]'
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

# EVID-48-BRIDGE-SANITIZER — Bridge sanitizer — baseline inspection

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

sanitize_bridge_payload recursively rejects forbidden fields, rejects unknown top-level keys, validates SanitizedBridgePayload and emits visible fields. VisibleBridgeAdapter.accept_observation_payload calls it before constructing Observation. This is the optional bridge integrity path, not a pixel-frame consumer.

## Evidence locator

Provenance: github_implementation. Checked: 2026-09-09.

[Source](https://github.com/Planton361/autonomous-game-agent/blob/7b4ec2e1497dec50c94b921b61dab42245bf5c90/src/fh_agent/bridge/sanitizer.py#L173) · sanitize_bridge_payload

## Registry relationships

- [[Evidence/EVID-48-BRIDGE-SANITIZER — Bridge sanitizer — baseline inspection|EVID-48-BRIDGE-SANITIZER · Bridge sanitizer — baseline inspection]] — `supports` → [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|CMP-NO-SPOILER-FIREWALL · No-Spoiler Firewall]]
- [[Evidence/EVID-48-BRIDGE-SANITIZER — Bridge sanitizer — baseline inspection|EVID-48-BRIDGE-SANITIZER · Bridge sanitizer — baseline inspection]] — `supports` → [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]]

[[Home/Research Atlas|Research Atlas Home]]
