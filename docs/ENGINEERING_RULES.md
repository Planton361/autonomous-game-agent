# Engineering rules

## 1. Minimal correct change

Make the smallest typed, testable change that satisfies the active milestone. Isolate side effects from pure logic.

## 2. Architecture authority

The canonical architecture governs enduring design; do not change canonical sources without explicit user review.

## 3. Evidence / no-spoiler

Game-specific facts, targets, and outcomes need evidence IDs. No hidden state, guide, or spoiler is official authority.

## 4. Runtime safety

No direct LLM key control, no game-specific Body shortcut, and no verifier self-confirmation. Wrong-window input must remain impossible through guarded execution.

## 5. Testing and verification

Use focused tests first where useful. Before publication, run full standard validation. Do not claim success from stale output.

## 6. Dependencies

Do not add large dependencies without rationale. Keep existing dependency and build choices unless a milestone authorizes a change.

## 7. Scientific reproducibility

No reward bypass of verified outcomes, no RL before reliable detectors, and no in-run Body-weight changes. Preserve provenance and run-mode separation.

## 8. Git / session discipline

Use the A2 branch → validate → explicit stage → commit → push → Draft PR → user merge workflow. One session normally serves one milestone.

## 9. Documentation discipline

Keep dynamic status in roadmap, milestones, and session reports. Canonical correctness, evidence, no-spoiler, and safety are never removable as “simplification.”
