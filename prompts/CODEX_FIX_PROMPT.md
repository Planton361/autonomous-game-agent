# Codex fix prompt

Fix exactly the named issue within the active milestone; do not broaden scope or continue another milestone.

## Outcome

[Expected corrected behavior.]

## Why

[Observed failure and impact.]

## Active milestone

`[docs/milestones/M-XXX-slug.md]`

## Scope

[Allowed files and behavior.]

## Non-goals

[Excluded refactors/features.]

## Relevant starting paths

[Failure evidence and relevant source/test paths.]

## Acceptance criteria

[Regression proof and invariant preservation.]

## Constraints

Apply claim-specific authority: GitHub HEAD + executable verification for implementation truth; active milestone for task; `docs/canonical/**` for stable research/architecture; `docs/ROADMAP.md` for progress; latest Session Report for last checks; explicit user decision for intent. Preserve no-spoiler, evidence, and input-safety boundaries.

## Verification

Reproduce, test the narrow fix, then run required standard validation.

## A2 Git handoff

Use the milestone branch; explicitly stage intended files; commit, push, Draft PR, and never merge or write the normal milestone directly to `main`.

## Stop conditions

Stop on scope or architecture expansion, untrustworthy validation, or three failed targeted hypotheses.

## Session Report

Record actual commands/results, changed files, handoff identifiers, and remaining risks.
