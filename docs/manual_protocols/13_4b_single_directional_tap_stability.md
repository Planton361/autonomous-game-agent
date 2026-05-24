# Milestone 13.4b Manual Protocol: Single Directional Tap Stability

## Purpose

Aggregate three separate manual 13.4-style bounded real directional tap runs. This is a report-only stability review: it reads existing JSON reports, validation outputs, and review outputs, and writes one aggregate JSON file.

Codex must not run the game, start automation, or send inputs for this protocol.

## Human Run Requirements

- Humans run three separate 13.4-style runs manually.
- Do not use Codex to run the game.
- Do not use a loop or script to perform three taps.
- Each run remains exactly one `move_right_short` with `max_input_count` 1.
- Do not use `confirm`, `cancel`, or `open_menu`.
- Each run must be validated and reviewed separately.
- Each run must include pre-input and post-input screenshot evidence with matching dimensions.
- Mechanical review plus manual visual review is required for each run before aggregation.
- After mechanical review, the human performs manual visual review and records it with `controlled-live-smoke-record-manual-review`; do not hand-edit JSON.

Manual visual review `passed` means the screenshots show the same game window, no OS permission dialog, and no interactive menu or dialogue requiring `confirm` or `cancel`. Ambient or automatic Overworld text is acceptable only if it does not require `confirm` or `cancel`.

Manual visual review `failed` must be used for OS permission dialogs, mismatched window, menus or dialogues needing input, or unclear evidence.

Record each manual visual review before aggregation:

```fish
uv run python -m fh_agent controlled-live-smoke-record-manual-review --review runs/run_13_4_single_directional_tap_01/reports/controlled_live_smoke_review.json --status passed --reviewer "<human name or initials>" --notes "same game window; no interactive prompt" --in-place
```

## Aggregate Review

After all three separate runs have passed their individual validator, mechanical review, and manual visual review, run the aggregate stability review on the resulting JSON files:

```fish
uv run python -m fh_agent controlled-live-smoke-stability-review \
  --report runs/run_13_4_single_directional_tap_01/reports/live_smoke_report.json \
  --validation runs/run_13_4_single_directional_tap_01/reports/live_smoke_report_validation.json \
  --review runs/run_13_4_single_directional_tap_01/reports/controlled_live_smoke_review.json \
  --report runs/run_13_4_single_directional_tap_02/reports/live_smoke_report.json \
  --validation runs/run_13_4_single_directional_tap_02/reports/live_smoke_report_validation.json \
  --review runs/run_13_4_single_directional_tap_02/reports/controlled_live_smoke_review.json \
  --report runs/run_13_4_single_directional_tap_03/reports/live_smoke_report.json \
  --validation runs/run_13_4_single_directional_tap_03/reports/live_smoke_report_validation.json \
  --review runs/run_13_4_single_directional_tap_03/reports/controlled_live_smoke_review.json \
  --output runs/run_13_4b_single_directional_tap_stability/reports/stability_review.json \
  --overwrite
```

The aggregate command must not call the live runner or input executor. It must fail unless all three runs are independent single directional tap runs with unique `run_id` values and manual visual review marked passed.
