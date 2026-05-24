import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fh_agent.evals.controlled_live_smoke_review import (
    record_controlled_live_smoke_manual_visual_review,
    write_controlled_live_smoke_manual_visual_review,
)
from fh_agent.evals.controlled_live_smoke_stability_review import (
    create_controlled_live_smoke_stability_review,
)

FIXED_CREATED_AT = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
ACTION = "move_right_short"


def test_13_4b_artifact_chain_passes_after_recording_three_manual_reviews(
    tmp_path: Path,
) -> None:
    artifacts = tuple(
        _write_run_artifacts_and_record_manual_review(tmp_path, f"run_13_4b_flow_{index}")
        for index in range(3)
    )

    summary = _aggregate(artifacts)

    assert summary.conclusion == "passed"
    assert summary.run_count == 3
    assert summary.total_inputs_sent == 3
    assert summary.max_inputs_sent_per_run == 1
    assert summary.allowed_real_primitives == ("move_right_short",)
    assert summary.all_validations_passed is True
    assert summary.all_reviews_passed is True
    assert summary.all_manual_visual_reviews_passed is True
    assert summary.all_pre_post_dimensions_match is True
    assert summary.all_focus_guard_immediate_before_input is True
    assert summary.all_emergency_stop_immediate_before_input is True
    assert summary.hidden_state_violation_count_total == 0
    assert summary.forbidden_input_count_total == 0
    assert summary.forbidden_executed_action_count_total == 0


def test_13_4b_artifact_chain_fails_when_one_manual_review_failed(tmp_path: Path) -> None:
    artifacts = (
        _write_run_artifacts_and_record_manual_review(
            tmp_path,
            "run_13_4b_flow_failed_manual",
            manual_status="failed",
        ),
        _write_run_artifacts_and_record_manual_review(tmp_path, "run_13_4b_flow_good_1"),
        _write_run_artifacts_and_record_manual_review(tmp_path, "run_13_4b_flow_good_2"),
    )

    summary = _aggregate(artifacts)

    assert summary.conclusion == "failed"
    assert summary.all_manual_visual_reviews_passed is False
    assert any(
        reason.endswith(":manual_visual_review_passed") for reason in summary.failure_reasons
    )


def test_13_4b_artifact_chain_fails_when_manual_review_status_missing(
    tmp_path: Path,
) -> None:
    artifacts = (
        _write_run_artifacts(tmp_path, "run_13_4b_flow_missing_manual"),
        _write_run_artifacts_and_record_manual_review(tmp_path, "run_13_4b_flow_good_1"),
        _write_run_artifacts_and_record_manual_review(tmp_path, "run_13_4b_flow_good_2"),
    )

    summary = _aggregate(artifacts)

    assert summary.conclusion == "failed"
    assert summary.all_manual_visual_reviews_passed is False
    assert any(
        reason.endswith(":manual_visual_review_passed") for reason in summary.failure_reasons
    )


def test_13_4b_artifact_chain_fails_when_one_run_sent_two_inputs(tmp_path: Path) -> None:
    artifacts = (
        _write_run_artifacts_and_record_manual_review(
            tmp_path,
            "run_13_4b_flow_two_inputs",
            report_updates={"inputs_sent": 2},
            review_updates={"inputs_sent": 2},
        ),
        _write_run_artifacts_and_record_manual_review(tmp_path, "run_13_4b_flow_good_1"),
        _write_run_artifacts_and_record_manual_review(tmp_path, "run_13_4b_flow_good_2"),
    )

    summary = _aggregate(artifacts)

    assert summary.conclusion == "failed"
    assert summary.max_inputs_sent_per_run == 2
    assert any(reason.endswith(":inputs_sent_one") for reason in summary.failure_reasons)


def test_13_4b_artifact_chain_fails_when_one_run_broadens_allowed_primitives(
    tmp_path: Path,
) -> None:
    artifacts = (
        _write_run_artifacts_and_record_manual_review(
            tmp_path,
            "run_13_4b_flow_wrong_primitive",
            report_updates={"allowed_real_primitives": ["move_right_short", "confirm"]},
            review_updates={"allowed_real_primitives": ["move_right_short", "confirm"]},
        ),
        _write_run_artifacts_and_record_manual_review(tmp_path, "run_13_4b_flow_good_1"),
        _write_run_artifacts_and_record_manual_review(tmp_path, "run_13_4b_flow_good_2"),
    )

    summary = _aggregate(artifacts)

    assert summary.conclusion == "failed"
    assert any(
        reason.endswith(":allowed_real_primitives_move_right_short")
        for reason in summary.failure_reasons
    )


def _write_run_artifacts_and_record_manual_review(
    tmp_path: Path,
    run_id: str,
    *,
    manual_status: Literal["passed", "failed"] = "passed",
    report_updates: dict[str, Any] | None = None,
    review_updates: dict[str, Any] | None = None,
) -> tuple[Path, Path, Path]:
    report_path, validation_path, review_path = _write_run_artifacts(
        tmp_path,
        run_id,
        report_updates=report_updates,
        review_updates=review_updates,
    )
    reviewed_payload = record_controlled_live_smoke_manual_visual_review(
        review_path=review_path,
        status=manual_status,
        notes="fixture manual visual review",
        reviewer="pytest",
        timestamp_utc=FIXED_CREATED_AT,
    )
    write_controlled_live_smoke_manual_visual_review(
        reviewed_payload,
        review_path,
        overwrite=True,
    )
    return report_path, validation_path, review_path


def _write_run_artifacts(
    tmp_path: Path,
    run_id: str,
    *,
    report_updates: dict[str, Any] | None = None,
    review_updates: dict[str, Any] | None = None,
) -> tuple[Path, Path, Path]:
    run_dir = tmp_path / "runs" / run_id
    reports_dir = run_dir / "reports"
    screenshots_dir = run_dir / "screenshots"
    reports_dir.mkdir(parents=True)
    screenshots_dir.mkdir(parents=True)
    pre_path = screenshots_dir / "pre.ppm"
    post_path = screenshots_dir / "post.ppm"
    pre_path.write_text("fixture pre screenshot bytes", encoding="utf-8")
    post_path.write_text("fixture post screenshot bytes", encoding="utf-8")

    report_path = reports_dir / "live_smoke_report.json"
    validation_path = reports_dir / "live_smoke_report_validation.json"
    review_path = reports_dir / "controlled_live_smoke_review.json"
    report = _report_payload(run_id=run_id, pre_path=pre_path, post_path=post_path)
    if report_updates is not None:
        report.update(report_updates)
    validation = _validation_payload(report_path)
    review = _mechanical_review_payload(
        run_id=run_id,
        report_path=report_path,
        validation_path=validation_path,
        review_path=review_path,
        report=report,
    )
    if review_updates is not None:
        review.update(review_updates)

    report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    validation_path.write_text(json.dumps(validation, sort_keys=True), encoding="utf-8")
    review_path.write_text(json.dumps(review, sort_keys=True), encoding="utf-8")
    return report_path, validation_path, review_path


def _aggregate(
    artifacts: tuple[tuple[Path, Path, Path], ...],
):
    return create_controlled_live_smoke_stability_review(
        report_paths=tuple(paths[0] for paths in artifacts),
        validation_paths=tuple(paths[1] for paths in artifacts),
        review_paths=tuple(paths[2] for paths in artifacts),
        created_at=FIXED_CREATED_AT,
    )


def _report_payload(*, run_id: str, pre_path: Path, post_path: Path) -> dict[str, Any]:
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
            _evidence("pre-evidence", pre_path, 640, 480),
            _evidence("post-evidence", post_path, 640, 480),
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


def _mechanical_review_payload(
    *,
    run_id: str,
    report_path: Path,
    validation_path: Path,
    review_path: Path,
    report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "review_summary_version": "1",
        "created_at": "2026-05-24T12:00:00Z",
        "run_id": run_id,
        "mode": "official_screen_only",
        "runtime_mode": "observation_only",
        "preflight_ok": True,
        "validator_passed": True,
        "validation_error_count": 0,
        "frame_count": 2,
        "captured_frame_count": 2,
        "min_frame_count": 2,
        "max_frame_count": 2,
        "screenshot_count": 2,
        "evidence_count": 2,
        "action_logging_mode": "disabled",
        "dryrun_orchestration_mode": "disabled",
        "real_input_mode": "single_directional_tap",
        "real_wait_only_active": False,
        "allowed_real_primitives": report["allowed_real_primitives"],
        "input_attempt_count": 1,
        "allowed_input_count": 1,
        "forbidden_input_count": 0,
        "executed_wait_count": 0,
        "forbidden_executed_action_count": 0,
        "focus_guard_check_count": 1,
        "focus_guard_pre_input_pass_count": 1,
        "emergency_stop_check_count": 1,
        "emergency_stop_pre_input_clear_count": 1,
        "rate_limit_enabled": False,
        "max_input_count": 1,
        "max_input_count_exceeded": False,
        "capture_script": "./scripts/capture_active_window_ppm.sh",
        "official_screen_only": True,
        "pre_input_evidence_count": 1,
        "post_input_evidence_count": 1,
        "dryrun_task_count": 0,
        "dryrun_skill_count": 0,
        "allowed_dryrun_task_count": 0,
        "forbidden_dryrun_task_count": 0,
        "allowed_dryrun_action_intent_count": 0,
        "forbidden_dryrun_action_intent_count": 0,
        "manager_dryrun_active": False,
        "body_dryrun_active": False,
        "actions_requested": 1,
        "inputs_sent": report["inputs_sent"],
        "allowed_action_intent_count": 1,
        "forbidden_action_intent_count": 0,
        "executed_action_count": report["executed_action_count"],
        "requested_action_names": [ACTION],
        "executed_action_names": [ACTION],
        "input_action_counters": {
            "actions_requested": 1,
            "inputs_sent": report["inputs_sent"],
        },
        "no_input_sent": False,
        "stop_reason": "max_frames_reached",
        "forbidden_runtime_markers_absent": True,
        "hidden_state_fields_absent": True,
        "planner_active": False,
        "manager_active": False,
        "body_active": False,
        "learning_active": False,
        "bridge_active": False,
        "ocr_active": False,
        "hidden_state_violation_count": 0,
        "automated_review_scope": "mechanical",
        "visual_review_required": True,
        "visual_review_status": "not_performed",
        "requires_manual_visual_review": True,
        "artifact_paths": {
            "preflight_report": str(report_path.with_name("preflight_report.json")),
            "live_audit_pipeline": str(report_path.with_name("live_audit_pipeline.json")),
            "live_smoke_report": str(report_path),
            "live_smoke_report_validation": str(validation_path),
            "review_summary": str(review_path),
        },
        "conclusion": "passed",
        "recommended_next_step": "manual visual review required",
        "failure_reasons": [],
    }


def _validation_payload(report_path: Path) -> dict[str, Any]:
    checks = [
        _validation_check("hidden_state_fields_absent"),
        _validation_check("forbidden_runtime_markers_absent"),
        _validation_check("single_directional_tap_input_safety"),
        _validation_check("single_directional_tap_pre_post_screenshot_evidence"),
    ]
    return {
        "validation_report_version": "1",
        "created_at": "2026-05-24T12:00:00Z",
        "source_report_path": str(report_path),
        "status": {
            "passed": True,
            "check_count": len(checks),
            "error_count": 0,
        },
        "checks": checks,
    }


def _action(name: str) -> dict[str, Any]:
    return {
        "action": name,
        "requested": True,
        "executed": True,
        "input_sent": True,
        "reason": "single_directional_tap",
        "frame_index": 0,
    }


def _evidence(evidence_id: str, path: Path, width: int, height: int) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "screenshot_path": str(path),
        "width": width,
        "height": height,
    }


def _validation_check(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": True,
        "severity": "info",
        "message": "fixture check passed",
    }
