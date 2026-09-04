---
name: minimal-change
description: Use when planning or applying a narrowly scoped change while preserving existing behavior and project invariants.
---

# Minimal change

Inspect relevant code and documentation before editing. Make the smallest correct, typed, testable change that satisfies the active GitHub Issue. Preserve established behavior unless the Issue explicitly changes it; isolate side effects and avoid unrelated refactors, formatting churn, or dependency changes.

Canonical correctness, evidence, no-spoiler, and safety are never removable as “simplification.” Stop if the smallest correct change needs scope or architecture expansion.
