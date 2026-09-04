# Operational roadmap

The stable capability sequence remains [`canonical/03_RESEARCH_ROADMAP_CANONICAL.md`](canonical/03_RESEARCH_ROADMAP_CANONICAL.md). It is not rewritten here.

## Planning rules

- M-IDs begin operationally at M-000R; completed pre-retrofit work is not renumbered.
- Preserve canonical phase and legacy working label as metadata.
- One milestone should fit one focused Codex session; technical microtasks are not permanent roadmap entries.
- Statuses are `proposed`, `ready`, `active`, `blocked`, and `done`.
- Only Blocking adoption debt may automatically create milestone work.

## Pre-retrofit history

- Phase A — completed before retrofit
- Phase B — completed before retrofit
- Phase C — completed
- Phase D — active
- Legacy C1–C6 completed before/at retrofit baseline

## Milestones

| ID | Canonical phase | Legacy label | Outcome | Risk | Status |
| --- | --- | --- | --- | --- | --- |
| M-000R | workflow | — | Repository workflow adoption | medium | done |
| M-001 | C | C7 | ManagerStopResult propagated to TaskCompletion | medium | done |
| M-002 | D | — | Canonical bridge-assisted run-mode contract | medium | done |
| M-003 | D | — | Bridge-assisted payloads exposed as ObservationSource | medium | done |
| M-004 | D | — | Bridge-assisted observations synchronized to durable screenshot evidence | medium | done |
| M-005 | D | — | Running Manager tasks execute through Body and independent Verifier | medium | done |
| M-006 | D | — | Cortex outputs constrained to evidence present in CortexContext | medium | done |
| M-007 | D | — | Evidence-bounded Cortex output submitted through Manager contract validation | medium | done |
| M-008 | D | — | Planner intent converted into current-evidence GroundingRequest | medium | done |
| M-009 | D | — | Cortex target intent grounded from current evidence before Manager submission | medium | done |
| M-010 | D | — | Planning observation preserved as first execution observation | medium | done |
| M-011R | D | M-011 blocker | Grounded targets round-trip through completion events and persistence | medium | done |
| M-011 | D | — | One hierarchical task runs Cortex → grounding → Manager → Body → Verifier → completion | medium | done |
| M-012 | D | — | Verifier-backed task outcomes become evidence-backed context for the next Cortex decision | medium | done |
| M-013 | D | — | Bounded hierarchical loop replans only from verifier-backed task outcomes | medium | done |
| M-014 | D | — | Append-only local JSONL feed supplies raw bridge payloads through existing no-spoiler boundaries | medium | done |
| M-015 | D | — | Concrete JSONL bridge ingress is composed with the bounded hierarchical replan runtime | medium | done |

Further Phase-D milestones will be cut after M-015 based on remaining exit-gate debt.
