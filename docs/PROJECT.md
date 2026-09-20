# Autonomous Game Agent — operational orientation

## Project

`Autonomous Game Agent`

## Purpose

Evidence-grounded hierarchical autonomous-agent research for long-horizon RPGs, with Fear & Hunger as the first pilot.

## Stable research sources

This page is operational orientation, not a replacement for the project charter. Stable research and architecture sources are:

- [`canonical/01_PROJECT_CHARTER.md`](canonical/01_PROJECT_CHARTER.md)
- [`canonical/02_ARCHITECTURE_CANONICAL.md`](canonical/02_ARCHITECTURE_CANONICAL.md)
- [`canonical/04_RESEARCH_PROTOCOL_CANONICAL.md`](canonical/04_RESEARCH_PROTOCOL_CANONICAL.md)

The accepted active `ALIGN-2026-09-19-v1.0` control release records the replacement
Mission Run/Life Episode semantics and simplified project workflow:
[`orchestration/releases/ALIGN-2026-09-19-v1.0/README.md`](orchestration/releases/ALIGN-2026-09-19-v1.0/README.md).

## Core non-negotiables

- Cortex never controls primitive keys directly; the Manager is the language/action authority.
- Body uses universal skills only, while an independent Verifier determines visible outcomes.
- Game-specific truth requires admissible evidence; hidden state and spoilers are not official authority.
- Body weights remain frozen within a Mission Run; death/restart creates a Life
  Episode and does not replace the controller.

## Repository orientation

The implementation is organized around `src/fh_agent/perception`, `observation`, `bridge`, `planner`, `manager`, `body`, `game`, `verifier`, `memory`, `evals`, and `rl`.

## Authority matrix

| Claim | Authority |
| --- | --- |
| What is actually implemented? | `main` HEAD + executable/CI verification |
| What should be implemented now? | Active GitHub Issue |
| What are long-term research / architecture rules? | `docs/canonical/**` |
| What defines capability order / phase exit gates? | `docs/canonical/03_RESEARCH_ROADMAP_CANONICAL.md` |
| What is the operational program? | GitHub Project |
| What is phase progress? | GitHub Milestone + Issues |
| What was last actually checked? | Pull Request and GitHub Actions records |
| What does literature support? | Checked primary source, version and locator |
| What did an experiment produce? | Frozen run/data identity + analysis evidence |
| What scientific claim is accepted? | Reviewed claim/evidence record or accepted project artifact |
| What is product / research intent? | Explicit user decision |

## Unified research and delivery lifecycle

The normal program flow is:

```text
Question / Need
→ RESEARCH
→ DECIDE/DESIGN / Protocol
→ EXPERIMENT
→ DELIVER when technical implementation is required
→ Evidence
→ EVALUATE
→ accepted Claim / Limitation
→ PAPER
```

`REVIEW` may independently inspect a frozen artifact. `LIVE` is a separate work class and
requires the applicable explicit Program Owner authorization.

The workflow keeps these epistemic states separate:

- literature finding and project hypothesis;
- hypothesis and accepted decision;
- implementation and experiment;
- unit/integration test and scientific result;
- experiment result and interpretation;
- interpretation and accepted claim;
- accepted claim and publishable wording.

Research may end without code. A valid experiment may reject its hypothesis.

The durable scientific provenance chain is:

```text
Research Question
→ Finding / Gap
→ accepted Decision or Protocol
→ Experiment Contract
→ frozen Run / Analysis identity
→ Evidence / Result
→ Evaluation
→ accepted Claim / Limitation
→ Manuscript reference
```

Research Atlas Registry data remains the public technical structured authority and its
generated views are disposable projections. The private Research Wiki remains a private
research workspace with one-way boundaries. Zotero remains literature/PDF authority.
GitHub remains the operational project authority. A private note is not an accepted claim
merely because it exists.

For an experiment, record proportional provenance as applicable: RQ/hypothesis,
treatment/comparator, frozen configuration, seeds/budgets, endpoints, data/run IDs,
exclusions/stop conditions, analysis plan, actual execution evidence, and limitations.

## Publication state

Current manuscript state is:

`NO_ACTIVE_MASTER`

Historical manuscript versions are references only. Future normal manuscript work requires
a separately accepted PAPER bootstrap that registers exactly one active Overleaf project
and exactly one canonical main source file. Until then, no chat, PDF, ZIP, DOCX, LaTeX tree,
or local file becomes an active manuscript master by convention. Missing results remain
missing.

## Delivery workflow

Routine work is planned as rolling-wave GitHub Issues under the Project and Phase A–N
Milestones. A Ready leaf Issue normally maps to one branch and one Draft Pull Request;
the user merges only after full GitHub CI and review. Issue closure drives Project Done.

The active GitHub Project is `Autonomous Game Agent — Research & Development` (Project #2).
Issues are the work items; Pull Requests are delivery evidence linked to Issues rather than
duplicate Project cards. Milestones remain real capability/scientific gates rather than
session trackers.

### Cross-device handoff

GitHub is the handoff authority between workstations. `origin/main` is the latest
accepted stable state, and one shared remote Issue branch (normally
`codex/<issue>-<slug>`) is the only active writer state for an Issue. Before
switching devices, the active workstation must have a clean working tree and its
local Issue-branch `HEAD` must equal the corresponding pushed remote branch
`HEAD`. A checkpoint commit is allowed for handoff, but it is not completion or
review evidence.

The receiving workstation must fetch with prune, check out the same Issue branch,
and fast-forward only from the remote before continuing. It must stop on local
dirt, divergence, an unexpected origin or tracking branch, or unresolved
conflicts. Direct work on `main`, automatic commit/push/merge, and synchronization
of generated caches, virtual environments, model caches, or machine-local
settings are not part of this workflow.

`uv run projectctl doctor` checks this state without fetching, pulling, committing,
pushing, installing tools, logging in, or changing authentication. Its optional
`--json` output is intended for later read-only workflow automation. A missing
`gh` or Codex CLI is reported as a warning; missing or stale local remote refs are
reported as unknown and never trigger an implicit network operation. A
remote-tracking ref is comparable only when its current object ID is recorded in
the local `FETCH_HEAD` for the active branch and the recorded fetch identity is
the expected repository; otherwise the relation remains unknown and the handoff
is not safe.

M-025 is the final historical M-XXX micro-milestone. New work does not create routine
milestone files, session reports, or manual roadmap rows; the existing M-000R–M-025
records remain historical artifacts.
