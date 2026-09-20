---
name: execute-issue
description: Use when executing one active GitHub Issue under its Work Type, authority, validation, and handoff rules.
---

# Execute issue

Read `AGENTS.md`, the active GitHub Issue, its applicable Milestone, and relevant Project
state before acting. Use `main` plus executable/CI verification for implementation truth;
the Issue for current scope; canonical sources for stable research/architecture and phase
exit gates; the Project for the operational program; and Pull Request/CI records for
executed technical checks.

Identify exactly one Work Type:

`Research | Decision/Design | Experiment | Delivery | Evaluation | Paper/Publication | Review | Live`

Execute one Issue only. Preserve canonical no-spoiler, evidence, run-integrity, and
input-safety rules. Keep literature findings, hypotheses, accepted decisions,
implementation, tests, experiment results, interpretations, accepted claims, and
publication wording distinct.

A new Issue, materially new contract, or different writer branch starts a fresh session.
A repair of the same Issue/contract/branch may resume. Use one writer per write branch.
A separate explorer or reviewer may run read-only.

Codex may execute a frozen experiment or analysis when the Issue authorizes it. It may not
silently change the RQ, hypothesis, treatment, comparator, endpoint, protocol, scientific
freeze, claim status, publication interpretation, architecture boundary, live
authorization, or merge authority.

When files change, apply the minimal-change and verify-change skills. Do not prepare or
implement a successor Issue unless the active Issue explicitly authorizes a future-contract
artifact.

For repository-writing work, publish only through the Issue flow:
`codex/<issue-number>-<slug>` → focused validation → explicit staging → commit → push →
Draft PR with `Closes #<issue-number>` → GitHub CI → review → explicit user merge.

Research, decision, evaluation, or review work that legitimately requires no repository
change does not need an artificial branch; its required durable result must still be
persisted at the authority named by the Issue.

Before merge, report only `ready for review`, `partial`, or `blocked`.

Use this concise return:

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
