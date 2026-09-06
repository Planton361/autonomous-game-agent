# Repository ChatGPT orchestration entry point

Current project orchestration is split between **TECH-ORCH** and **SCI-ORCH** under
`ALIGN-2026-09-06-v1.0`; this file is only a repository routing entry and is not a third
permanent orchestrator role. Start from
[`docs/canonical/00_ACTIVE_SOURCE_INDEX.md`](docs/canonical/00_ACTIVE_SOURCE_INDEX.md),
then read the applicable role and shared workflow in
[`docs/canonical/10_ORCHESTRATOR_MANDATES.md`](docs/canonical/10_ORCHESTRATOR_MANDATES.md)
and [`docs/canonical/08_ORCHESTRATION_PROTOCOL.md`](docs/canonical/08_ORCHESTRATION_PROTOCOL.md).

Use claim-specific authority: read the active GitHub Issue for current scope,
`docs/canonical/**` for stable research, architecture, capability order, and phase exit gates,
`main` HEAD plus executable/CI verification for material implementation claims, the GitHub
Project for the operational program, GitHub Milestones and Issues for phase progress, and
Pull Request/CI records for last executed checks.

Ask only questions that change scope, architecture, or risk. Do not invent requirements.
Produce exactly one next Codex Issue contract when more work is needed, and do not continue
another Issue in the same Codex task. Normal work uses
`codex/<issue-number>-<slug>` → focused local validation → Draft PR with
`Closes #<issue-number>` → GitHub CI → review → explicit user merge. Before merge, report
only `ready for review`, `partial`, or `blocked`.

The current user decision is authoritative for intent, but durable decisions must be written back to repository artifacts. Do not duplicate canonical prose.
