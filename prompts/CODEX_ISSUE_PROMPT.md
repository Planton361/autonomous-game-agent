# Codex GitHub Issue prompt

Execute exactly one active GitHub Issue. Do not implement a successor Issue or Phase-D
product work unless the Issue explicitly authorizes it.

## Outcome

[State the observable Issue outcome.]

## Why now

[State the decision, user value, or risk addressed.]

## Active GitHub Issue

`[#<issue-number> — <title>]`

## Scope

[Allowed paths and intended changes.]

## Non-goals / stop conditions

[Explicit exclusions, baseline drift, required architecture decision, or validation block.]

## Relevant starting paths

[Issue, canonical sources, relevant code/tests, Project/Milestone, and existing PR/CI evidence.]

## Acceptance criteria

[Observable Issue criteria.]

## Constraints

Use claim-specific authority: `main` HEAD plus executable/CI verification for implementation
truth; the active Issue for current work; `docs/canonical/**` for long-term research,
architecture, capability order, and phase exit gates; the GitHub Project and Milestone for
operational program and phase state; Pull Request/CI records for executed checks; and explicit
user decisions for intent. Preserve evidence, no-spoiler, run integrity, and input safety.

## Verification

[Focused local checks. Run full local validation only for a high-risk boundary, CI
unavailability, global repair, CI-workflow change, phase exit, or explicit user request.]

## GitHub handoff

Branch `codex/<issue-number>-<slug>`; validate; explicitly stage intended files; commit; push;
create a Draft PR with `Closes #<issue-number>`; wait for full GitHub CI and review; user merge
only. Before merge, report `ready for review`, `partial`, or `blocked`.
