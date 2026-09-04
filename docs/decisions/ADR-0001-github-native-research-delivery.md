# ADR-0001: GitHub-native Research Delivery Pipeline v1

Status: accepted

## Context

The historical M-XXX milestone, session-report, and manual-roadmap workflow duplicated
operational state that GitHub Projects, Milestones, Issues, Pull Requests, and Actions can
represent directly. The canonical research sources remain the authority for research and
architecture; the operational delivery mechanism must not become a second architecture source.

## Decision

- Use one GitHub Project as the operational program view.
- Map canonical Phase A–N one-to-one to GitHub Milestones; canonical phase order and exit gates
  remain authoritative.
- Use GitHub Issues for bounded work and outcome records, with rolling-wave planning and a
  default work-in-progress limit of one.
- Let a leaf Issue normally map to one Pull Request.
- Use focused local validation for ordinary work and full GitHub CI for Pull Requests; run full
  local validation only for high-risk boundaries, CI changes or unavailability, global repair,
  phase exits, or explicit user request.
- Require explicit user merge after CI and review. A Draft Pull Request is not completion.
- Let Issue closure drive Project Done. Do not configure Project Done to close an Issue.
- Close a Phase Milestone only when its canonical exit gate has been demonstrated, not merely
  when its implementation Issues close.
- Treat M-025 as the historical cutoff for the global M-XXX scheme. Preserve M-000R–M-025
  milestone and session-report artifacts unchanged, and do not create routine replacements.

## Consequences

Dynamic program state is maintained in GitHub rather than manual roadmap rows or per-PR session
reports. New Codex work starts from a Ready GitHub Issue, uses a
`codex/<issue-number>-<slug>` branch, and hands off through a Draft Pull Request with full CI.
Before merge, Codex reports `ready for review`, `partial`, or `blocked`.

Canonical sources, evidence requirements, no-spoiler constraints, run-mode eligibility, and
input-safety boundaries remain unchanged.

## Evidence / references

- GitHub Issue #28 — Adopt GitHub-native Research Delivery Pipeline v1
- `docs/canonical/03_RESEARCH_ROADMAP_CANONICAL.md`
- `AGENTS.md`
- Historical `docs/milestones/M-000R-*` through `M-025-*` and `docs/session-reports/`
