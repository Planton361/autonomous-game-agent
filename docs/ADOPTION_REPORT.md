# M-000R workflow adoption report

## Previous workflow

The project used GitHub HEAD, frozen canonical sources, and the current chat; Codex tickets were delivered through chat. Normal work used direct validated commit/push to `main`, without repo-local milestone contracts or session reports, repo-local skills/custom Codex reviewer, or a standard PR boundary for normal milestones.

## Current technical state

The retrofit baseline is `c9a3793777b5c0fc224c8bfa5cc8a9a7506c671c`. The project uses Python >=3.12, uv + `uv.lock`, Pydantic, pytest, Ruff, and a Typer/Rich CLI, with SQLite/JSONL/evidence artifacts. No typechecker, repository CI workflow, or container baseline is configured. It is a scientific/no-spoiler project; Phase C is active, and the baseline includes `ManagerStopResult`. `configs/experiments/pilot_fh.yaml` is a historical preregistration snapshot and must not be used as authority for current implementation state.

## Existing agent / AI setup

The baseline contained a root `AGENTS.md`, no pre-retrofit `.agents/`, no pre-retrofit `.codex/`, and no pre-retrofit PR template/workflow. A provider-neutral local LLM client exists in product code but is unrelated to the Codex workflow. The old chat workflow was operational orchestration.

## Conflicts found

### Conflict 1 — Chat temporary state vs repository handoff

Sources: frozen source index, previous workflow, and the explicit M-000R user decision.

Resolution: operational dynamic state moves into ROADMAP, milestone, and session-report sources.

Reason: chats must not be required to resume work.

### Conflict 2 — direct main vs A2

Resolution: A2 starts at M-000R merge; history remains untouched.

### Conflict 3 — root ROADMAP

Resolution: the root file becomes a compatibility link to operational and canonical roadmaps.

### Conflict 4 — `pilot_fh.yaml` drift

Resolution: it is a historical preregistration snapshot, remains unchanged, and is not current-state authority.

Observed drift includes old debt/gate values and references to `docs/research/NO_SPOILER_PROTOCOL.md` and `docs/research/METRICS.md`. Do not repair it here.

### Conflict 5 — universal source hierarchy

Resolution: use a claim-specific authority matrix.

### Conflict 6 — Greenfield M-000/M-001

Resolution: use M-000R and the next true open slice M-001/C7; do not retrospectively renumber work.

### Conflict 7 — hardcoded model names

Resolution: use capability profiles only.

### Conflict 8 — protected-main assumption

Resolution: the workflow prohibition is active; server-side enforcement is UNKNOWN and not part of this retrofit.

## Decisions preserved

Python 3.12, uv, current dependencies, source layout, pytest/Ruff, canonical research architecture, no-spoiler policy, run-mode separation, provider-neutral Cortex, existing product code, current test strategy, historical preregistration, and the absence of CI/Docker/typechecker migration remain unchanged.

## Decisions replaced

Direct-main milestone publication, chat-exclusive handoff, chat-derived operational roadmap state, generic Greenfield milestone numbering, a generic universal source hierarchy, and starter hardcoded model mappings are replaced.

## Deferred improvements

### Blocking

None.

### Opportunistic

- GitHub server-side branch protection/ruleset
- CI if future maintenance demonstrates value
- a successor versioned pilot experiment configuration before a new confirmatory experiment
- later cleanup of historical noncanonical docs/config references only through explicit research/versioning decisions

### Cosmetic

- README navigation refinements
- documentation presentation polish

Opportunistic and Cosmetic items do not automatically create roadmap work.

## New source of truth

| Claim | Authority |
| --- | --- |
| What is actually implemented? | GitHub HEAD + executable verification |
| What should be implemented now? | Active milestone contract |
| What are long-term research / architecture rules? | `docs/canonical/**` |
| What is operational project progress? | `docs/ROADMAP.md` |
| What was last actually checked? | Latest Session Report |
| What is product / research intent? | Explicit user decision |

## Workflow baseline

Retrofit technical baseline: `c9a3793777b5c0fc224c8bfa5cc8a9a7506c671c`.

The new workflow becomes active only when the M-000R Draft PR is explicitly merged by the user. If this report is committed before PR creation, the GitHub PR remains the external durable merge record.
