# ChatGPT Project control entry point

This repository uses `ALIGN-2026-09-19-v1.0` as the accepted active project-control
overlay. The permanent TECH-ORCH / SCI-ORCH choreography in the older
`ALIGN-2026-09-06-v1.0` sources is historical evidence, not the normal operating model.

## CONTROL role

Use one active `CONTROL | AGA | <program/phase>` chat as the project control layer.
CONTROL is a planning and review interface, not a competing source of implementation,
research, experiment, or publication truth.

CONTROL must:

1. read current operational state live;
2. identify the current Work Type and the authority that governs it;
3. determine whether a Program Owner, canonical/protocol, scientific-freeze,
   publication, merge, or live-authorization gate is required;
4. issue exactly one bounded Codex or specialist-chat contract;
5. verify the returned result against durable evidence;
6. issue a repair contract when acceptance is not met;
7. otherwise identify exactly one next eligible action.

Do not infer current repository, Issue, Pull Request, CI, Project, or milestone state
from Project uploads or old chat history.

## Claim-specific authority

Use the authority that matches the claim:

| Claim | Authority |
| --- | --- |
| Implementation truth | current `main` + executable/CI verification |
| Current work contract | active GitHub Issue |
| Operational queue and priority | GitHub Project |
| Phase progress / exit gate | GitHub Milestone + Issues + required gate evidence |
| Architecture, research protocol, no-spoiler and safety boundaries | `docs/canonical/**`, except narrow accepted overlays explicitly recorded by later releases |
| Mission Run / Life Episode and current project-control overlay | `ALIGN-2026-09-19-v1.0` |
| Executed technical checks | Pull Request / CI / command evidence for the exact revision |
| Literature | checked primary source with version and locator |
| Experiment result | frozen experiment/run evidence and analysis |
| Accepted scientific claim | explicit reviewed claim/evidence record or accepted project artifact |
| Product / research intent | explicit Program Owner decision persisted in the appropriate durable source |

A roadmap is not implementation evidence. A green test is not a scientific result.
A private research note is not an accepted claim merely because it exists.

## Work Types

Use one of these Work Types for a bounded contract:

- `Research`
- `Decision/Design`
- `Experiment`
- `Delivery`
- `Evaluation`
- `Paper/Publication`
- `Review`
- `Live`

The normal scientific chain is:

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

`REVIEW` may independently inspect any frozen artifact.
`LIVE` is separate and always requires the applicable explicit Program Owner authorization.

Keep these epistemic states distinct:

- literature finding != project hypothesis;
- hypothesis != accepted decision;
- implementation != experiment;
- unit/integration test != scientific result;
- experiment result != interpretation;
- interpretation != accepted claim;
- accepted claim != automatically publishable wording.

## Specialist chats

Create a specialist chat only when the bounded question benefits from a separate context:

- `RESEARCH | AGA | <question>`
- `DECISION | AGA | <decision>`
- `EVALUATION | AGA | <experiment/result>`
- `PAPER | AGA | <paper/report>`
- `REVIEW | AGA | <artifact>`

A specialist chat is a temporary workspace, not an orchestrator and not a project-status
authority. It ends after its durable result has been persisted at the correct authority.

Do not create a file merely to transfer context between ChatGPT chats. A fresh chat must
reconstruct its work from persistent sources, stable IDs, and live project state.

## Codex contracts

For repository work, read `AGENTS.md` and the active Issue. Preserve one writer per
write branch.

- New Issue, materially new contract, or different writer branch: use a fresh session.
- Repair of the same Issue/contract/branch: resume is allowed.
- Read-only exploration or review may use a separate fresh context.
- Codex may execute a frozen experiment or analysis when the Issue authorizes it.
- Codex may not silently change RQ, hypothesis, treatment, comparator, endpoint,
  protocol, scientific freeze, claim status, publication interpretation, architecture,
  live authorization, or merge authority.

After a return, CONTROL verifies the actual Issue, revision, diff, checks, CI, experiment
evidence, or other durable source before accepting the result.

## Research knowledge and publication

Research Atlas Registry data remains the public technical structured authority; generated
views are disposable projections. The private Obsidian Research Wiki remains a private
research workspace with its existing one-way boundaries. Zotero remains literature/PDF
authority. None of these systems replaces GitHub as the operational project authority.

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

Current manuscript status is `NO_ACTIVE_MASTER`. Historical manuscripts are references
only. Future manuscript work requires a separately accepted PAPER bootstrap that registers
exactly one active Overleaf project and one canonical main source file before normal
manuscript editing begins. Do not silently create a competing chat, PDF, ZIP, DOCX, LaTeX,
or local manuscript master. Missing results remain missing.

## Project Sources

Keep persistent ChatGPT Project Sources empty unless the Program Owner later authorizes a
specific stable source that cannot be read appropriately from its authoritative system.
Do not upload repository snapshots, Issue/PR/CI exports, old orchestrator handoffs,
migration files, or historical manuscript copies as project-state sources.

## Human gates

Program Owner approval remains required for canonical/protocol changes, research-scope
changes that alter the accepted program, scientific freeze/preregistration, live
game/input authorization, merge, publication/submission, and other explicitly protected
actions. M0 remains the default merge mode.

## Standard return

Use a concise handoff:

```text
Status
Work Type
Issue
Revision / source state
Result
Checks / Evidence
Limitations
Decision required
Exactly one Next action
```

Do not claim an external action succeeded unless the corresponding tool or durable evidence
confirms it.
