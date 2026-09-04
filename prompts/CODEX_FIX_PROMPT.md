# Codex Issue fix prompt

Fix exactly the active GitHub Issue; do not broaden scope or implement a successor Issue.

## Outcome

[Expected corrected behavior.]

## Why

[Observed failure and impact.]

## Active GitHub Issue

`[#<issue-number> — <title>]`

## Scope

[Allowed files and behavior.]

## Non-goals

[Excluded refactors/features.]

## Relevant starting paths

[Failure evidence and relevant source/test paths.]

## Acceptance criteria

[Regression proof and invariant preservation.]

## Constraints

Apply claim-specific authority: `main` HEAD + executable/CI verification for implementation truth; active Issue for task; `docs/canonical/**` for stable research/architecture and phase exit gates; GitHub Project/Milestone for program and phase state; Pull Request/CI records for last checks; and explicit user decision for intent. Preserve no-spoiler, evidence, and input-safety boundaries.

## Verification

Reproduce, test the narrow fix, then run required standard validation.

## A2 Git handoff

Use `codex/<issue-number>-<slug>`; explicitly stage intended files; commit, push, create a Draft PR with `Closes #<issue-number>`, and never merge or write normal work directly to `main`.

## Stop conditions

Stop on scope or architecture expansion, untrustworthy validation, or three failed targeted hypotheses.

## Pull Request handoff

Record actual commands/results, changed files, handoff identifiers, and remaining risks in the Pull Request. Before merge, report `ready for review`, `partial`, or `blocked`.
