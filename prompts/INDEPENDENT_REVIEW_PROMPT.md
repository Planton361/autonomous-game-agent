# Independent Issue review prompt

Review the named GitHub Issue and Draft Pull Request read-only. Do not edit, commit, push, or merge.

## Outcome

[Issue outcome.]

## Why

[Risk or user value.]

## Active GitHub Issue

`[#<issue-number> — <title>]`

## Scope

[Expected paths/change class.]

## Non-goals

[Excluded work.]

## Relevant starting paths

[Issue, Project/Milestone context, Draft PR diff, relevant sources/tests, and CI evidence.]

## Acceptance criteria

[Criteria to independently verify.]

## Constraints

Use claim-specific authority rather than a universal hierarchy. Inspect GitHub HEAD and executable evidence for implementation claims; use canonical sources only for stable research/architecture. Focus on correctness/regression, security/permissions, data integrity, scientific validity where applicable, missing risk-relevant tests, and scope creep. Ignore style-only findings.

## Verification

[Read-only review commands and evidence.]

## GitHub handoff

Review only; return findings for the executing branch/Draft PR. Do not merge or close the Issue.

## Stop conditions

Stop and mark blocked if the evidence is insufficient for a risk-relevant decision.

## Pull Request evidence

State whether the Pull Request faithfully records actual local and CI evidence.

Classify findings as `Blocker`, `Relevant`, `Optional`, or `No issue`; conclude `approve`, `fixes required`, or `blocked`.
