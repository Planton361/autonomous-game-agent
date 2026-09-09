---
atlas_id: CMP-VISIBLE-STATE-BRIDGE
atlas_type: Component
atlas_name: Optional Visible-State Bridge
atlas_level: L2
atlas_generated: true
registry_schema_version: '0.2'
overview_visibility: main
overview_order: 28
research_mapping: unmapped
research_direction: null
architecture_authority: canonical-target
implementation_status: implemented
verification_status: unverified
observes:
- '[[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE
  · Game / Environment]]'
part_of:
- '[[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game
  Agent Experiment System]]'
presented_in_domain:
- '[[Architecture/Domains/DOM-ENV-ACQUISITION — Environment & Acquisition|DOM-ENV-ACQUISITION
  · Environment & Acquisition]]'
supports_from: &id001
- '[[Evidence/EVID-48-BRIDGE — Bridge — baseline inspection|EVID-48-BRIDGE · Bridge
  — baseline inspection]]'
- '[[Evidence/EVID-48-BRIDGE-SANITIZER — Bridge sanitizer — baseline inspection|EVID-48-BRIDGE-SANITIZER
  · Bridge sanitizer — baseline inspection]]'
- '[[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical
  Ingress]]'
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

# CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Optional bridge-assisted adapter checks declared mode and latest durable screenshot binding. Payloads pass the deny-by-default sanitizer/firewall; this is not a bypass or primary screen-only perception.

## Classification

Architecture authority: canonical-target. Implementation: implemented. Verification: unverified.

Implementation is not live demonstration; integration tests are not measurement validation. Target-only does not mean a research gap.

## Registry relationships

- [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]] — `observes` → [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]
- [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]] — `part_of` → [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]] — `presented_in_domain` → [[Architecture/Domains/DOM-ENV-ACQUISITION — Environment & Acquisition|DOM-ENV-ACQUISITION · Environment & Acquisition]]
- [[Evidence/EVID-48-BRIDGE — Bridge — baseline inspection|EVID-48-BRIDGE · Bridge — baseline inspection]] — `supports` → [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]]
- [[Evidence/EVID-48-BRIDGE-SANITIZER — Bridge sanitizer — baseline inspection|EVID-48-BRIDGE-SANITIZER · Bridge sanitizer — baseline inspection]] — `supports` → [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]]
- [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|EVID-48-CANON-INGRESS · Canonical Ingress]] — `supports` → [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]]

[[Home/Research Atlas|Research Atlas Home]]
