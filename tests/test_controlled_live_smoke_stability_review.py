import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from fh_agent.cli import app
from fh_agent.evals.controlled_live_smoke_stability_review import (
    create_controlled_live_smoke_stability_review,
    write_controlled_live_smoke_stability_review,
)

FIXED_CREATED_AT = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
ACTION = "move_right_short"


def _action(name: str) -> dict[str, Any]:
    return {
        "action": name,
        "requested": True,
        "executed": True,
        "input_sent": True,
        "reason": "single_directional_tap",
        "frame_index": 0,
    }


def _evidence(evidence_id: str, path: str, width: int, height: int) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "screenshot_path": path,
        "width": width,
        "height": height,
    }


def write_run_artifacts(
    tmp_path: Path,
    run_id: str,
    *,
    report_updates: dict[str, Any] | None = None,
    validation_passed: bool = True,
    failed_validation_check: str | None = None,
    review_updates: dict[str, Any] | None = None,
) -> tuple[Path, Path, Path]:
    run_dir = tmp_path / "runs" / run_id
    reports_dir = run_dir / "reports"
    screenshots_dir = run_dir / "screenshots"
    reports_dir.mkdir(parents=True)
    screenshots_dir.mkdir(parents=True)
    pre_path = screenshots_dir / "pre.ppm"
    post_path = screenshots_dir / "post.ppm"
    pre_path.write_text("P3\n1 1\n255\n0 0 0\n", encoding="utf-8")
    post_path.write_text("P3\n1 1\n255\n0 0 0\n", encoding="utf-8")

    report_path = reports_dir / "live_smoke_report.json"
    validation_path = reports_dir / "live_smoke_report_validation.json"
    review_path = reports_dir / "controlled_live_smoke_review.json"
    report = _valid_report(
        run_id=run_id,
        pre_path=pre_path,
        post_path=post_path,
    )
    if report_updates:
        _deep_update(report, report_updates)

    checks = [
        _validation_check("hidden_state_fields_absent", True),
        _validation_check("forbidden_runtime_markers_absent", True),
        _validation_check("single_directional_tap_input_safety", True),
        _validation_check("single_directional_tap_pre_post_screenshot_evidence", True),
    ]
    if failed_validation_check is not None:
        checks = [
            check | {"passed": False, "severity": "error"}
            if check["name"] == failed_validation_check
            else check
            for check in checks
        ]
    if not validation_passed and failed_validation_check is None:
        checks[2] = checks[2] | {"passed": False, "severity": "error"}
    error_count = sum(1 for check in checks if not check["passed"])
    validation = {
        "validation_report_version": "1",
        "created_at": "2026-05-24T12:00:00Z",
        "source_report_path": str(report_path),
        "status": {
            "passed": validation_passed and error_count == 0,
            "check_count": len(checks),
            "error_count": error_count,
        },
        "checks": checks,
    }
    review = _valid_review(
        run_id=str(report.get("run_id", run_id)),
        report_path=report_path,
        validation_path=validation_path,
        review_path=review_path,
        report=report,
        validator_passed=validation["status"]["passed"],
        validation_error_count=error_count,
    )
    if review_updates:
        _deep_update(review, review_updates)

    report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    validation_path.write_text(json.dumps(validation, sort_keys=True), encoding="utf-8")
    review_path.write_text(json.dumps(review, sort_keys=True), encoding="utf-8")
    return report_path, validation_path, review_path


def create_summary(
    triples: tuple[tuple[Path, Path, Path], ...],
):
    return create_controlled_live_smoke_stability_review(
        report_paths=tuple(paths[0] for paths in triples),
        validation_paths=tuple(paths[1] for paths in triples),
        review_paths=tuple(paths[2] for paths in triples),
        created_at=FIXED_CREATED_AT,
    )


def valid_triples(tmp_path: Path) -> tuple[tuple[Path, Path, Path], ...]:
    return tuple(write_run_artifacts(tmp_path, f"run_13_4b_{index}") for index in range(3))


def test_stability_review_passes_with_exactly_three_valid_independent_single_tap_runs(
    tmp_path: Path,
) -> None:
    summary = create_summary(valid_triples(tmp_path))

    assert summary.conclusion == "passed"
    assert summary.run_count == 3
    assert summary.run_ids == ("run_13_4b_0", "run_13_4b_1", "run_13_4b_2")
    assert summary.real_input_mode == "single_directional_tap"
    assert summary.allowed_real_primitives == ("move_right_short",)
    assert summary.total_inputs_sent == 3
    assert summary.total_executed_action_count == 3
    assert summary.max_inputs_sent_per_run == 1
    assert summary.max_executed_action_count_per_run == 1
    assert summary.forbidden_input_count_total == 0
    assert summary.forbidden_executed_action_count_total == 0
    assert summary.hidden_state_violation_count_total == 0
    assert summary.all_validations_passed is True
    assert summary.all_reviews_passed is True
    assert summary.all_manual_visual_reviews_passed is True
    assert summary.all_pre_post_dimensions_match is True
    assert summary.all_focus_guard_immediate_before_input is True
    assert summary.all_emergency_stop_immediate_before_input is True


def test_stability_review_rejects_fewer_than_three_runs(tmp_path: Path) -> None:
    summary = create_summary(valid_triples(tmp_path)[:2])

    assert summary.conclusion == "failed"
    assert "run_count_3" in summary.failure_reasons


def test_stability_review_rejects_duplicate_run_id(tmp_path: Path) -> None:
    triples = (
        write_run_artifacts(tmp_path, "duplicate_a", report_updates={"run_id": "same"}),
        write_run_artifacts(tmp_path, "duplicate_b", report_updates={"run_id": "same"}),
        write_run_artifacts(tmp_path, "duplicate_c", report_updates={"run_id": "same"}),
    )

    summary = create_summary(triples)

    assert summary.conclusion == "failed"
    assert "unique_run_ids" in summary.failure_reasons


@pytest.mark.parametrize(
    ("report_updates", "review_updates", "reason"),
    [
        ({"inputs_sent": 2}, {"inputs_sent": 2}, "inputs_sent_one"),
        ({"executed_action_count": 2}, {"executed_action_count": 2}, "executed_action_count_one"),
        (
            {
                "allowed_real_primitives": ["move_left_short"],
                "requested_actions": [_action("move_left_short")],
                "executed_actions": [_action("move_left_short")],
            },
            {
                "allowed_real_primitives": ["move_left_short"],
                "requested_action_names": ["move_left_short"],
                "executed_action_names": ["move_left_short"],
            },
            "allowed_real_primitives_move_right_short",
        ),
        (
            {"requested_actions": [_action("confirm")], "executed_actions": [_action("confirm")]},
            {"requested_action_names": ["confirm"], "executed_action_names": ["confirm"]},
            "no_confirm_cancel_open_menu",
        ),
        (
            {"requested_actions": [_action("cancel")], "executed_actions": [_action("cancel")]},
            {"requested_action_names": ["cancel"], "executed_action_names": ["cancel"]},
            "no_confirm_cancel_open_menu",
        ),
        (
            {
                "requested_actions": [_action("open_menu")],
                "executed_actions": [_action("open_menu")],
            },
            {"requested_action_names": ["open_menu"], "executed_action_names": ["open_menu"]},
            "no_confirm_cancel_open_menu",
        ),
        ({"forbidden_input_count": 1}, {"forbidden_input_count": 1}, "forbidden_input_count_zero"),
        (
            {"forbidden_executed_action_count": 1},
            {"forbidden_executed_action_count": 1},
            "forbidden_executed_action_count_zero",
        ),
        (
            {"hidden_state_violation_count": 1},
            {"hidden_state_violation_count": 1},
            "hidden_state_violation_count_zero",
        ),
        ({"official_screen_only": False}, {"official_screen_only": False}, "official_screen_only"),
        (
            {"autonomous_planner_active": True},
            {"planner_active": True},
            "no_bridge_planner_llm_ocr_rl_active_flags",
        ),
        (
            {"manager_orchestration_active": True},
            {"manager_active": True},
            "no_bridge_planner_llm_ocr_rl_active_flags",
        ),
        (
            {"body_control_active": True},
            {"body_active": True},
            "no_bridge_planner_llm_ocr_rl_active_flags",
        ),
        (
            {"bridge_active": True},
            {"bridge_active": True},
            "no_bridge_planner_llm_ocr_rl_active_flags",
        ),
        ({"llm_active": True}, {}, "no_bridge_planner_llm_ocr_rl_active_flags"),
        ({"ocr_active": True}, {"ocr_active": True}, "no_bridge_planner_llm_ocr_rl_active_flags"),
        ({"rl_active": True}, {}, "no_bridge_planner_llm_ocr_rl_active_flags"),
        (
            {"learning_active": True},
            {"learning_active": True},
            "no_bridge_planner_llm_ocr_rl_active_flags",
        ),
        (
            {"pre_input_evidence_ids": []},
            {"pre_input_evidence_count": 0},
            "pre_screenshot_evidence_present",
        ),
        (
            {"post_input_evidence_ids": []},
            {"post_input_evidence_count": 0},
            "post_screenshot_evidence_present",
        ),
        (
            {
                "screenshot_evidence": [
                    _evidence("pre-evidence", "pre.ppm", 640, 480),
                    _evidence("post-evidence", "post.ppm", 800, 600),
                ],
            },
            {},
            "pre_post_dimensions_match",
        ),
        (
            {"focus_guard_check_count": 0, "focus_guard_pre_input_pass_count": 0},
            {"focus_guard_check_count": 0, "focus_guard_pre_input_pass_count": 0},
            "focus_guard_immediate_before_input",
        ),
        (
            {"emergency_stop_check_count": 0, "emergency_stop_pre_input_clear_count": 0},
            {"emergency_stop_check_count": 0, "emergency_stop_pre_input_clear_count": 0},
            "emergency_stop_immediate_before_input",
        ),
    ],
)
def test_stability_review_rejects_invalid_single_tap_run_fields(
    tmp_path: Path,
    report_updates: dict[str, Any],
    review_updates: dict[str, Any],
    reason: str,
) -> None:
    triples = (
        write_run_artifacts(
            tmp_path,
            "run_bad",
            report_updates=report_updates,
            review_updates=review_updates,
        ),
        write_run_artifacts(tmp_path, "run_good_1"),
        write_run_artifacts(tmp_path, "run_good_2"),
    )

    summary = create_summary(triples)

    assert summary.conclusion == "failed"
    assert any(item.endswith(f":{reason}") for item in summary.failure_reasons)


def test_stability_review_rejects_failed_validator(tmp_path: Path) -> None:
    triples = (
        write_run_artifacts(tmp_path, "run_bad", validation_passed=False),
        write_run_artifacts(tmp_path, "run_good_1"),
        write_run_artifacts(tmp_path, "run_good_2"),
    )

    summary = create_summary(triples)

    assert summary.conclusion == "failed"
    assert any(item.endswith(":validator_passed") for item in summary.failure_reasons)


def test_stability_review_rejects_failed_mechanical_review(tmp_path: Path) -> None:
    triples = (
        write_run_artifacts(
            tmp_path,
            "run_bad",
            review_updates={"conclusion": "failed", "failure_reasons": ["synthetic"]},
        ),
        write_run_artifacts(tmp_path, "run_good_1"),
        write_run_artifacts(tmp_path, "run_good_2"),
    )

    summary = create_summary(triples)

    assert summary.conclusion == "failed"
    assert any(item.endswith(":mechanical_review_passed") for item in summary.failure_reasons)


def test_stability_review_rejects_missing_manual_visual_review_pass(tmp_path: Path) -> None:
    triples = (
        write_run_artifacts(tmp_path, "run_bad", review_updates={"visual_review_status": "failed"}),
        write_run_artifacts(tmp_path, "run_good_1"),
        write_run_artifacts(tmp_path, "run_good_2"),
    )

    summary = create_summary(triples)

    assert summary.conclusion == "failed"
    assert summary.all_manual_visual_reviews_passed is False
    assert any(item.endswith(":manual_visual_review_passed") for item in summary.failure_reasons)


def test_stability_review_rejects_failed_pre_post_dimension_validation_check(
    tmp_path: Path,
) -> None:
    triples = (
        write_run_artifacts(
            tmp_path,
            "run_bad",
            failed_validation_check="single_directional_tap_pre_post_screenshot_evidence",
        ),
        write_run_artifacts(tmp_path, "run_good_1"),
        write_run_artifacts(tmp_path, "run_good_2"),
    )

    summary = create_summary(triples)

    assert summary.conclusion == "failed"
    assert any(item.endswith(":pre_post_dimensions_match") for item in summary.failure_reasons)


def test_stability_review_missing_file_has_clear_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    with pytest.raises(ValueError, match="review file does not exist"):
        create_controlled_live_smoke_stability_review(review_paths=(missing,))


def test_stability_review_writer_refuses_to_overwrite(tmp_path: Path) -> None:
    summary = create_summary(valid_triples(tmp_path))
    output = tmp_path / "stability.json"

    write_controlled_live_smoke_stability_review(summary, output)

    with pytest.raises(FileExistsError, match="already exists"):
        write_controlled_live_smoke_stability_review(summary, output)


def test_cli_help_includes_stability_review_command() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "controlled-live-smoke-stability-review" in result.output


def test_cli_stability_review_help() -> None:
    result = CliRunner().invoke(app, ["controlled-live-smoke-stability-review", "--help"])

    assert result.exit_code == 0
    assert "--report" in result.output
    assert "--validation" in result.output
    assert "--review" in result.output
    assert "--output" in result.output


def test_cli_stability_review_writes_passing_summary(tmp_path: Path) -> None:
    triples = valid_triples(tmp_path)
    output = tmp_path / "stability.json"
    args = ["controlled-live-smoke-stability-review", "--output", str(output)]
    for index in range(3):
        args.extend(["--report", str(triples[index][0])])
        args.extend(["--validation", str(triples[index][1])])
        args.extend(["--review", str(triples[index][2])])

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "passed"
    assert payload["run_count"] == 3
    assert payload["total_inputs_sent"] == 3


def _valid_report(*, run_id: str, pre_path: Path, post_path: Path) -> dict[str, Any]:
    action = _action(ACTION)
    return {
        "run_id": run_id,
        "mode": "official_screen_only",
        "runtime_mode": "observation_only",
        "official_screen_only": True,
        "real_input_mode": "single_directional_tap",
        "action_logging_mode": "disabled",
        "dryrun_orchestration_mode": "disabled",
        "allowed_real_primitives": [ACTION],
        "status": {"actions_requested": 1, "stop_reason": "max_frames_reached"},
        "input_attempt_count": 1,
        "allowed_input_count": 1,
        "forbidden_input_count": 0,
        "inputs_sent": 1,
        "no_input_sent": False,
        "executed_action_count": 1,
        "executed_wait_count": 0,
        "forbidden_executed_action_count": 0,
        "focus_guard_check_count": 1,
        "focus_guard_pre_input_pass_count": 1,
        "emergency_stop_check_count": 1,
        "emergency_stop_pre_input_clear_count": 1,
        "max_input_count": 1,
        "max_input_count_exceeded": False,
        "hidden_state_violation_count": 0,
        "requested_actions": [action],
        "executed_actions": [action],
        "pre_input_evidence_ids": ["pre-evidence"],
        "post_input_evidence_ids": ["post-evidence"],
        "screenshot_evidence": [
            _evidence("pre-evidence", str(pre_path), 640, 480),
            _evidence("post-evidence", str(post_path), 640, 480),
        ],
        "autonomous_planner_active": False,
        "manager_orchestration_active": False,
        "body_control_active": False,
        "bridge_active": False,
        "llm_active": False,
        "ocr_active": False,
        "rl_active": False,
        "learning_active": False,
    }


def _valid_review(
    *,
    run_id: str,
    report_path: Path,
    validation_path: Path,
    review_path: Path,
    report: dict[str, Any],
    validator_passed: bool,
    validation_error_count: int,
) -> dict[str, Any]:
    return {
        "review_summary_version": "1",
        "created_at": "2026-05-24T12:00:00Z",
        "run_id": run_id,
        "mode": report["mode"],
        "runtime_mode": "observation_only",
        "preflight_ok": True,
        "validator_passed": validator_passed,
        "validation_error_count": validation_error_count,
        "frame_count": 2,
        "captured_frame_count": 2,
        "min_frame_count": 2,
        "max_frame_count": 2,
        "screenshot_count": 2,
        "evidence_count": 2,
        "action_logging_mode": "disabled",
        "dryrun_orchestration_mode": "disabled",
        "real_input_mode": report["real_input_mode"],
        "real_wait_only_active": False,
        "allowed_real_primitives": report["allowed_real_primitives"],
        "input_attempt_count": report["input_attempt_count"],
        "allowed_input_count": report["allowed_input_count"],
        "forbidden_input_count": report["forbidden_input_count"],
        "executed_wait_count": report["executed_wait_count"],
        "forbidden_executed_action_count": report["forbidden_executed_action_count"],
        "focus_guard_check_count": report["focus_guard_check_count"],
        "focus_guard_pre_input_pass_count": report["focus_guard_pre_input_pass_count"],
        "emergency_stop_check_count": report["emergency_stop_check_count"],
        "emergency_stop_pre_input_clear_count": report["emergency_stop_pre_input_clear_count"],
        "rate_limit_enabled": False,
        "max_input_count": report["max_input_count"],
        "max_input_count_exceeded": report["max_input_count_exceeded"],
        "capture_script": "./scripts/capture_active_window_ppm.sh",
        "official_screen_only": report["official_screen_only"],
        "pre_input_evidence_count": len(report.get("pre_input_evidence_ids", [])),
        "post_input_evidence_count": len(report.get("post_input_evidence_ids", [])),
        "dryrun_task_count": 0,
        "dryrun_skill_count": 0,
        "allowed_dryrun_task_count": 0,
        "forbidden_dryrun_task_count": 0,
        "allowed_dryrun_action_intent_count": 0,
        "forbidden_dryrun_action_intent_count": 0,
        "manager_dryrun_active": False,
        "body_dryrun_active": False,
        "actions_requested": report["status"]["actions_requested"],
        "inputs_sent": report["inputs_sent"],
        "allowed_action_intent_count": 1,
        "forbidden_action_intent_count": 0,
        "executed_action_count": report["executed_action_count"],
        "requested_action_names": [ACTION],
        "executed_action_names": [ACTION],
        "input_action_counters": {
            "actions_requested": report["status"]["actions_requested"],
            "inputs_sent": report["inputs_sent"],
        },
        "no_input_sent": report["no_input_sent"],
        "stop_reason": "max_frames_reached",
        "forbidden_runtime_markers_absent": True,
        "hidden_state_fields_absent": True,
        "planner_active": False,
        "manager_active": False,
        "body_active": False,
        "learning_active": False,
        "bridge_active": False,
        "ocr_active": False,
        "hidden_state_violation_count": report["hidden_state_violation_count"],
        "automated_review_scope": "mechanical",
        "visual_review_required": True,
        "visual_review_status": "passed",
        "requires_manual_visual_review": True,
        "artifact_paths": {
            "preflight_report": str(report_path.with_name("preflight_report.json")),
            "live_audit_pipeline": str(report_path.with_name("live_audit_pipeline.json")),
            "live_smoke_report": str(report_path),
            "live_smoke_report_validation": str(validation_path),
            "review_summary": str(review_path),
        },
        "conclusion": "passed",
        "recommended_next_step": "aggregate stability review",
        "failure_reasons": [],
    }


def _validation_check(name: str, passed: bool) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "severity": "info" if passed else "error",
        "message": "ok" if passed else "failed",
    }


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
