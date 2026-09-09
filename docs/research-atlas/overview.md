# Research Atlas v0.1

SYS-AGA — Autonomous Game Agent

Generated from registry/{nodes,relationships,evidence}.yaml; do not edit.
Domains group navigation only; they are neither technical parents nor canonical taxonomy.
Connections describe targets as well as implementation; consult each node's status.
Dossier sections point into the registry; their ID lists do not author relationships.

## DOM-ACTION-SAFETY — Action & Safety

No pilot component mapped.

## DOM-COGNITION — Cognition

- [CMP-CORTEX](dossiers/CMP-CORTEX.md) — Cortex: canonical-target; implemented; integration-tested; research mapping: unmapped.

## DOM-ENV-ACQUISITION — Environment & Acquisition

No pilot component mapped.

## DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval

- [CMP-MEM-RETRIEVAL](dossiers/CMP-MEM-RETRIEVAL.md) — Memory Retrieval: canonical-target; partial; unverified; research mapping: unmapped.

## DOM-EXECUTIVE — Executive Control & Contracts

- [CMP-MANAGER](dossiers/CMP-MANAGER.md) — Manager: canonical-target; implemented; integration-tested; research mapping: unmapped.

## DOM-OBS-INTEGRITY-STATE — Observation Integrity & State

No pilot component mapped.

## DOM-VERIFY-LEARN — Verification & Learning

No pilot component mapped.

## Interface and contract connections

- `CMP-CORTEX` — consumes → `CON-CORTEX-CONTEXT`
- `CMP-CORTEX` — consumes → `IF-MEM-CORTEX`
- `CMP-CORTEX` — supplies → `CON-PLANNER-OUTPUT`
- `CMP-CORTEX` — supplies → `IF-CORTEX-MANAGER`
- `CMP-MANAGER` — consumes → `CON-PLANNER-OUTPUT`
- `CMP-MANAGER` — consumes → `IF-CORTEX-MANAGER`
- `CMP-MANAGER` — supplies → `CON-SKILL-CONTRACT`
- `CMP-MEM-RETRIEVAL` — supplies → `IF-MEM-CORTEX`

## Indicators

3 pilot components; 7 presentation domains; 4 measurement mappings; 22 evidence records.
Papers: 0; findings: 0; contradictions: 0.
No literature review, gap analysis, or automatic research-status promotion in this pilot.
