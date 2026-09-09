---
atlas_id: EVID-48-TRAINING-LIMIT
atlas_type: Evidence
atlas_name: Training Limit — baseline inspection
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
path: src/fh_agent/rl/behavior_cloning.py
symbol: build_behavior_cloning_dataset
line: 71
supports:
- '[[Components/CMP-BODY-CERTIFICATION — Body Validation - Certification|CMP-BODY-CERTIFICATION
  · Body Validation / Certification]]'
- '[[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]]'
- '[[Data Artifacts/DAT-CANDIDATE-BODY-VERSION — Candidate Body Version|DAT-CANDIDATE-BODY-VERSION
  · Candidate Body Version]]'
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

# EVID-48-TRAINING-LIMIT — Training Limit — baseline inspection

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

build_behavior_cloning_dataset converts synthetic replay transitions to supervised examples, optionally filtering positive rewards. It does not train weights, create versioned Body candidates, certify or activate controllers. Inspection of baseline rl/body source found no such lifecycle; the three between-run nodes remain target-only.

## Evidence locator

Provenance: github_implementation. Checked: 2026-09-09.

[Source](https://github.com/Planton361/autonomous-game-agent/blob/7b4ec2e1497dec50c94b921b61dab42245bf5c90/src/fh_agent/rl/behavior_cloning.py#L71) · build_behavior_cloning_dataset

## Registry relationships

- [[Evidence/EVID-48-TRAINING-LIMIT — Training Limit — baseline inspection|EVID-48-TRAINING-LIMIT · Training Limit — baseline inspection]] — `supports` → [[Components/CMP-BODY-CERTIFICATION — Body Validation - Certification|CMP-BODY-CERTIFICATION · Body Validation / Certification]]
- [[Evidence/EVID-48-TRAINING-LIMIT — Training Limit — baseline inspection|EVID-48-TRAINING-LIMIT · Training Limit — baseline inspection]] — `supports` → [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]]
- [[Evidence/EVID-48-TRAINING-LIMIT — Training Limit — baseline inspection|EVID-48-TRAINING-LIMIT · Training Limit — baseline inspection]] — `supports` → [[Data Artifacts/DAT-CANDIDATE-BODY-VERSION — Candidate Body Version|DAT-CANDIDATE-BODY-VERSION · Candidate Body Version]]

[[Home/Research Atlas|Research Atlas Home]]
