# Milestone 13.4b Artifact Workflow Handoff

## Purpose

This runbook covers the manual artifact workflow for bounded single directional tap stability.

- 13.4b proves repeatable bounded single directional tap stability across three separate manual runs.
- 13.4c records manual visual review without hand-editing JSON.
- 13.4d fixture-tests the artifact chain from mechanical review JSON through manual review recording to stability aggregation.

Codex must not run the game, send inputs, call the live runner, call the input executor, inspect screenshots automatically, or use Planner/LLM, Bridge, OCR, RL, or hidden-state access for this workflow.

## Manual Workflow

Run three separate 13.4-style `single_directional_tap` runs manually.

Each run must:

- Use `official_screen_only`.
- Allow only `move_right_short`.
- Keep `max_input_count == 1`.
- Produce exactly one real input.
- Include pre-input and post-input screenshot evidence.
- Validate and mechanically review its own artifacts before aggregation.

Do not use one script or loop to perform three taps. Do not use `confirm`, `cancel`, `open_menu`, Planner, Bridge, OCR, or RL.

## Per-Run Artifacts

Expected paths for each run:

```text
runs/<run_id>/reports/live_smoke_report.json
runs/<run_id>/reports/live_smoke_report_validation.json
runs/<run_id>/reports/controlled_live_smoke_review.json
```

## Manual Visual Review Recorder

After mechanical review, a human reviews the pre/post screenshots and records the result with the file-only recorder:

```fish
uv run python -m fh_agent controlled-live-smoke-record-manual-review \
  --review runs/<run_id>/reports/controlled_live_smoke_review.json \
  --status passed \
  --reviewer "<initials>" \
  --notes "same game window; no OS permission dialog; ambient text only; no interactive prompt" \
  --in-place
```

Use `--status failed` when the visual review fails. Do not hand-edit review JSON.

## Aggregate Stability Review

Run the aggregate review with repeated `--report`, `--validation`, and `--review` arguments for exactly three runs:

```fish
uv run python -m fh_agent controlled-live-smoke-stability-review \
  --report runs/<run_id_01>/reports/live_smoke_report.json \
  --validation runs/<run_id_01>/reports/live_smoke_report_validation.json \
  --review runs/<run_id_01>/reports/controlled_live_smoke_review.json \
  --report runs/<run_id_02>/reports/live_smoke_report.json \
  --validation runs/<run_id_02>/reports/live_smoke_report_validation.json \
  --review runs/<run_id_02>/reports/controlled_live_smoke_review.json \
  --report runs/<run_id_03>/reports/live_smoke_report.json \
  --validation runs/<run_id_03>/reports/live_smoke_report_validation.json \
  --review runs/<run_id_03>/reports/controlled_live_smoke_review.json \
  --output runs/run_13_4b_single_directional_tap_stability_01/reports/stability_review.json \
  --overwrite
```

## Pass Criteria

The aggregate review passes only when all of these are true:

- Exactly three unique `run_id` values.
- All validations passed.
- All mechanical reviews passed.
- All manual visual reviews passed.
- `total_inputs_sent == 3`.
- `max_inputs_sent_per_run == 1`.
- `allowed_real_primitives == ["move_right_short"]`.
- `hidden_state_violation_count_total == 0`.
- `forbidden_input_count_total == 0`.
- `forbidden_executed_action_count_total == 0`.
- `all_pre_post_dimensions_match == true`.
- `all_focus_guard_immediate_before_input == true`.
- `all_emergency_stop_immediate_before_input == true`.

## Manual Visual Review Guidance

Pass only if:

- The same game window is visible before and after.
- No KDE/Wayland permission dialog is visible.
- No OS or system prompt is visible.
- No interactive menu or dialogue requiring `confirm` or `cancel` is visible.
- Ambient Overworld text is automatic and non-interactive.

Fail if:

- A permission dialog appears.
- Pre/post dimensions mismatch.
- The wrong window is captured.
- A menu or dialogue requires input.
- Evidence is unclear.

## Troubleshooting

KDE/Wayland permission dialog:
Resolve the OS permission state outside the official run, discard the affected run, and rerun manually only after the prompt is gone.

Pre/post dimension mismatch:
Treat as a failed run. This can indicate a focus steal, OS prompt, wrong window, or resized window.

Failed manual review:
Record `--status failed`. Do not aggregate the run as passing. Create a fresh manual run after resolving the visible issue.

Aggregate rejects missing `visual_review_status`:
Run `controlled-live-smoke-record-manual-review` for each run before aggregation.

Aggregate rejects broadened primitives:
Discard that run. Each run must allow only `move_right_short`; do not add `confirm`, `cancel`, `open_menu`, or any other primitive.

## End Condition

If the aggregate review passes, Milestone 13.4b stability is complete.

The next architecture step should be decided in ChatGPT before any broader action set or longer live run is attempted.
