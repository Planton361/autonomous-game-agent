---
name: execute-issue
description: Use when executing one active GitHub Issue under its declared scope, authority, validation, and Pull Request handoff rules.
---

# Execute issue

Read `AGENTS.md`, the active GitHub Issue, its Phase Milestone, and relevant Project state before acting. Use `main` HEAD plus executable/CI verification for implementation truth; the Issue for current scope; canonical sources for stable research/architecture and phase exit gates; the Project for operational program state; and Pull Request/CI records for executed checks.

Execute one Issue only. Preserve canonical no-spoiler, evidence, run-integrity, and input-safety rules. Apply the minimal-change and verify-change skills. Do not prepare or implement a successor Issue unless the active Issue explicitly authorizes a future-contract artifact.

Publish only through the Issue flow: `codex/<issue-number>-<slug>`, focused local validation, explicit staging, commit, push, Draft PR with `Closes #<issue-number>`, full GitHub CI, review, then explicit user merge. Before merge, report only `ready for review`, `partial`, or `blocked`.
