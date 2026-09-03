# Codex milestone prompt

Execute exactly one milestone under A2. Do not implement a successor milestone.

## Outcome

[State the desired observable result.]

## Why

[State the decision or problem this resolves.]

## Active milestone

`[docs/milestones/M-XXX-slug.md]`

## Scope

[Allowed paths and intended changes.]

## Non-goals

[Explicit exclusions.]

## Relevant starting paths

[Paths to inspect before editing.]

## Acceptance criteria

[Observable criteria.]

## Constraints

Use claim-specific authority: GitHub HEAD + executable verification for implementation truth; active milestone for current task; `docs/canonical/**` for long-term research/architecture; `docs/ROADMAP.md` for operational progress; latest Session Report for last checks; explicit user decision for product/research intent. Preserve evidence, no-spoiler, run integrity, and input safety.

## Verification

[Targeted checks, followed by the project standard validation.]

## A2 Git handoff

Branch `codex/<milestone>-<slug>`; validate; stage intended files only; commit; push; Draft PR; no merge and no direct normal-milestone write to `main`.

## Stop conditions

[Baseline drift, dirty worktree, scope/architecture expansion, validation block, or three failed targeted fixes.]

## Session Report

Create or update the current Session Report with actual baseline and final validation evidence, changed-file scope, commit, PR, and residual risks.
