# Engineering rules

## 1. Minimal correct change

Make the smallest typed, testable change that satisfies the active GitHub Issue. Isolate side effects from pure logic.

## 2. Architecture authority

The canonical architecture governs enduring design; do not change canonical sources without explicit user review.

## 3. Evidence / no-spoiler

Game-specific facts, targets, and outcomes need evidence IDs. No hidden state, guide, or spoiler is official authority.

## 4. Runtime safety

No direct LLM key control, no game-specific Body shortcut, and no verifier self-confirmation. Wrong-window input must remain impossible through guarded execution.

## 5. Testing and verification

Use focused tests and static checks locally for ordinary Issue work. GitHub Actions runs the full standard suite on Pull Requests and pushes to `main`. Run the full local suite only for a high-risk boundary, CI unavailability, global repair, CI-workflow change, phase exit, or explicit user request. Do not claim success from stale output.

## 6. Dependencies

Do not add large dependencies without rationale. Keep existing dependency and build choices unless the active GitHub Issue authorizes a change.

## 7. Scientific reproducibility

No reward bypass of verified outcomes, no RL before reliable detectors, and no in-run Body-weight changes. Preserve provenance and run-mode separation.

## 8. Git / Issue discipline

Use the Ready GitHub Issue → `codex/<issue-number>-<slug>` → focused local validation → explicit stage → commit → push → Draft PR (`Closes #<issue-number>`) → GitHub CI → review → user merge workflow. Do not merge or write normal work directly to `main`. A Draft PR is `ready for review`, `partial`, or `blocked`, never automatically `done`.

## 9. Documentation discipline

Keep dynamic status in the GitHub Project, Milestones, Issues, Pull Requests, and CI. M-025 is the historical cutoff for routine milestone/session-report records; do not add manual roadmap rows for new work. Canonical correctness, evidence, no-spoiler, and safety are never removable as “simplification.”
