# Milestone 13.4 Manual Protocol: Single Directional Tap

## Purpose

Prepare and run the first bounded real directional tap: exactly one `move_right_short` in `official_screen_only` mode, with one pre-input screenshot/evidence record and one post-input screenshot/evidence record.

Codex must not run this protocol, start the game, or send inputs.

## Preconditions

- Milestone 13.3 and 13.3b reports have been reviewed and passed.
- The user has manually started the game.
- The user has manually positioned the character in a safe visible area.
- The tile or space immediately to the right is visibly safe and empty.
- No visible dialogue/text box, menu, combat UI, death screen, screen transition, loading state, OS permission dialog, or uncertain state is active.
- Before any official 13.4 rerun, grant, deny, or otherwise resolve OS input-control permission prompts outside the run.
- Abort if the visible setup is unsafe or uncertain.

## Manual Run Command

Run this from a terminal, then focus the game window during the 3 second sleep:

```fish
sleep 3; uv run python -m fh_agent controlled-live-smoke --pipeline-summary runs/run_13_3b_real_wait_only_noop_03/reports/live_audit_pipeline.json --user-started --allow-real-runtime --allow-real-input --real-input-mode single_directional_tap --allowed-real-primitive move_right_short --max-input-count 1 --max-frames 2 --target-window-title "Fear & Hunger" --capture-command ./scripts/capture_active_window_ppm.sh --run-dir runs/run_13_4_single_directional_tap --overwrite
```

Do not use `confirm`, `cancel`, or `open_menu`. If a KDE/Wayland or other OS permission prompt appears, abort and mark the run failed. After a successful live run, do not repeat it; validate and review the existing artifacts first.

## Expected Outputs

- `runs/run_13_4_single_directional_tap/reports/live_smoke_report.json`
- `runs/run_13_4_single_directional_tap/screenshots/*.ppm`
- Pre-input evidence listed in `pre_input_evidence_ids`
- Post-input evidence listed in `post_input_evidence_ids`
- Post-input screenshot evidence must still show the game window with the same dimensions as the pre-input screenshot evidence.

## Validation

```fish
uv run python -m fh_agent controlled-live-smoke-validate --report runs/run_13_4_single_directional_tap/reports/live_smoke_report.json --expected-frame-count 2 --output runs/run_13_4_single_directional_tap/reports/live_smoke_report_validation.json --overwrite
```

## Review

```fish
uv run python -m fh_agent controlled-live-smoke-review --run-dir runs/run_13_4_single_directional_tap --min-frame-count 2 --max-frame-count 2 --overwrite
```

Do not count the run as passed until manual screenshot visual review confirms the same game window before and after the tap, with no visible text box/dialogue, menu, combat, loading, death, or OS permission dialog.

## Rollback

After the run, the user manually moves the character back or reloads if needed. There is no automated rollback.
