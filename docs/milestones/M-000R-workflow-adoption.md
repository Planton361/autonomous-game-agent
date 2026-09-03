---
id: M-000R
status: done
risk: medium
model_profile: critical
autonomy: A2
review: recommended
merge_authorized: false
branch: codex/m000r-workflow-adoption
retrofit_baseline: c9a3793777b5c0fc224c8bfa5cc8a9a7506c671c
---

# M-000R — Workflow Adoption

## Outcome

Repository-based milestone/session-report workflow established without product-code changes.

## Why

Remove dependency on chat memory and direct-main implementation sessions while preserving canonical research rules.

## Baseline gate

```bash
git fetch origin
git switch main
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
uv run fh-agent --help
```

## In scope

Only workflow, documentation, agent, prompt, review, and session-report artifacts listed in the M-000R task contract.

## Out of scope

- product code
- M-001/C7
- architecture refactor
- dependency migration
- new typechecker
- Docker
- CI
- test-coverage campaign
- canonical sources
- historical preregistration edits
- live runtime

## Acceptance criteria

- Claim-specific authority is consistent across operative sources.
- A2 branch/PR workflow is consistent everywhere; no normal direct-main rule remains.
- Canonical files and pilot snapshot are unchanged.
- Exactly the selected six repo-local skills and one reviewer exist.
- Reproducible environment commands are documented and executed.
- Baseline validation and fresh post-change validation are recorded.
- M-001 is ready, but not implemented; a Session Report exists.
- A Draft PR is created, with no unintended production, test, or dependency changes.

## Relevant sources / paths

`AGENTS.md`, root `ROADMAP.md`, `docs/canonical/**`, `configs/experiments/pilot_fh.yaml`, and the M-000R allowed changed-file list.

## Technical constraints

Canonical correctness, evidence, no-spoiler, and input safety remain intact. The pilot configuration is a historical preregistration snapshot, not implementation authority.

## Verification

Run the baseline gate on the unchanged baseline, then fresh standard validation and the CLI smoke after edits. Inspect the complete diff, allowed file scope, canonical/pilot zero diffs, obsolete workflow matches, model-name matches, TOML parsing, and `git diff -- src tests`.

## Git handoff

Use `codex/m000r-workflow-adoption`, explicitly stage intended files, commit, push, and create a Draft PR. Do not merge.

## Stop conditions

Stop for baseline drift, dirty workspace, scope expansion, need to modify canonical sources, need to alter product code, an unavailable environment that prevents trustworthy validation, or three failed targeted fixes.
