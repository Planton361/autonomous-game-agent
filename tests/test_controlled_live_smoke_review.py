import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.evals.controlled_live_smoke_review as review_module
from fh_agent.cli import app
from fh_agent.evals.controlled_live_smoke_review import (
    PASSED_NEXT_STEP,
    SINGLE_TAP_MECHANICAL_NEXT_STEP,
    create_controlled_live_smoke_review_summary,
    record_controlled_live_smoke_manual_visual_review,
    write_controlled_live_smoke_manual_visual_review,
    write_controlled_live_smoke_review_summary,
)

FIXED_CREATED_AT = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)


def write_review_fixture(
    tmp_path: Path,
    *,
    frame_count: int = 3,
    validator_passed: bool = True,
    validation_error_count: int = 0,
    include_validation_report: bool = True,
    include_preflight_report: bool = True,
    include_pipeline_summary: bool = True,
    no_input_sent: bool = True,
    actions_requested: int = 0,
    inputs_sent: int = 0,
    action_logging_mode: str = "disabled",
    dryrun_orchestration_mode: str = "disabled",
    real_input_mode: str = "disabled",
    real_inputs_sent: int = 0,
    single_directional_tap: bool = False,
    single_action: str = "move_right_short",
    include_post_evidence: bool = True,
    real_forbidden_input_count: int = 0,
    real_focus_guard_check_count: int | None = None,
    real_emergency_stop_check_count: int | None = None,
    real_capture_script: str = "./scripts/capture_active_window_ppm.sh",
    dryrun_action: str = "wait",
    dryrun_selected_skill: str = "wait",
    dryrun_executed: bool = False,
    dryrun_input_sent: bool = False,
    requested_action: str = "wait",
    requested_action_executed: bool = False,
    requested_action_input_sent: bool = False,
    planner_active: bool = False,
    manager_active: bool = False,
    body_active: bool = False,
    learning_active: bool = False,
    bridge_active: bool = False,
    hidden_state_violation_count: int = 0,
    hidden_state_check_passed: bool = True,
    forbidden_marker_check_passed: bool = True,
    screenshot_count_delta: int = 0,
    evidence_count_delta: int = 0,
) -> Path:
    run_dir = tmp_path / "runs" / "run_12_10b_three_frame_manual"
    reports_dir = run_dir / "reports"
    screenshots_dir = run_dir / "screenshots"
    reports_dir.mkdir(parents=True)
    screenshots_dir.mkdir(parents=True)
    screenshot_paths = []
    evidence_ids = []
    screenshot_count = frame_count + screenshot_count_delta
    evidence_count = frame_count + evidence_count_delta
    for index in range(max(screenshot_count, evidence_count)):
        evidence_id = f"evidence-{index}"
        screenshot_path = screenshots_dir / f"{evidence_id}.ppm"
        screenshot_path.write_bytes(b"P6\n1 1\n255\nabc")
        if index < screenshot_count:
            screenshot_paths.append(str(screenshot_path))
        if index < evidence_count:
            evidence_ids.append(evidence_id)
    requested_actions = [
        {
            "action": requested_action,
            "requested": True,
            "executed": requested_action_executed,
            "input_sent": requested_action_input_sent,
            "reason": "noop_action_logging",
            "frame_index": index,
        }
        for index in range(actions_requested)
    ]
    dryrun_tasks = []
    real_wait_only = real_input_mode == "wait_only_noop"
    real_single_tap = real_input_mode == "single_directional_tap" or single_directional_tap
    if dryrun_orchestration_mode == "wait_only":
        dryrun_action_intent = {
            "action": dryrun_action,
            "requested": True,
            "executed": dryrun_executed,
            "input_sent": dryrun_input_sent,
            "reason": "dryrun_orchestration_wait_only",
            "frame_index": 0,
        }
        requested_actions = [dryrun_action_intent]
        dryrun_tasks = [
            {
                "task_id": "dryrun-wait-0",
                "static_goal": "maintain_observation_without_input",
                "selected_skill": dryrun_selected_skill,
                "action_intent": dryrun_action_intent,
            }
        ]
    if real_wait_only:
        requested_actions = [
            {
                "action": "wait",
                "requested": True,
                "executed": True,
                "input_sent": True,
                "reason": "real_wait_only_noop",
                "frame_index": index,
            }
            for index in range(real_inputs_sent)
        ]
        actions_requested = real_inputs_sent
        inputs_sent = real_inputs_sent
        no_input_sent = False
    if real_single_tap:
        real_input_mode = "single_directional_tap"
        requested_actions = [
            {
                "action": single_action,
                "requested": True,
                "executed": True,
                "input_sent": True,
                "reason": "single_directional_tap",
                "frame_index": 0,
            }
        ]
        actions_requested = 1
        inputs_sent = real_inputs_sent or 1
        no_input_sent = False

    if include_preflight_report:
        (reports_dir / "preflight_report.json").write_text(
            json.dumps(
                {
                    "ok": True,
                    "checks": [],
                    "run_id": "run_12_10b_three_frame_manual",
                    "notes": [],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    if include_pipeline_summary:
        (reports_dir / "live_audit_pipeline.json").write_text(
            json.dumps(
                {
                    "pipeline_version": "1",
                    "run_id": "run_12_10b_three_frame_manual",
                    "created_at": "2026-05-17T12:00:00Z",
                    "execution_enabled": False,
                    "official_run_allowed": True,
                    "mode": "official_screen_only",
                    "preflight_report_path": str(reports_dir / "preflight_report.json"),
                    "manifest_path": str(reports_dir / "live_run_manifest.json"),
                    "smoke_plan_path": str(reports_dir / "live_smoke_plan.json"),
                    "smoke_report_path": str(reports_dir / "live_smoke_report.json"),
                    "summary_path": str(reports_dir / "live_audit_pipeline.json"),
                    "stages": [],
                    "validation_errors": [],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    (reports_dir / "live_smoke_report.json").write_text(
        json.dumps(
            {
                "report_version": "1",
                "run_id": "run_12_10b_three_frame_manual",
                "created_at": "2026-05-17T12:00:00Z",
                "user_started": True,
                "allow_real_input": real_wait_only or real_single_tap,
                "execution_enabled": False,
                "official_run_allowed": True,
                "mode": "official_screen_only",
                "status": {
                    "started": True,
                    "finished": True,
                    "stop_reason": "max_frames_reached",
                    "frames_captured": frame_count,
                    "actions_requested": actions_requested,
                },
                "event_count": 6,
                "runtime_mode": "observation_only",
                "no_input_sent": no_input_sent,
                "inputs_sent": inputs_sent,
                "action_logging_mode": action_logging_mode,
                "dryrun_orchestration_mode": dryrun_orchestration_mode,
                "real_input_mode": real_input_mode,
                "real_wait_only_active": real_wait_only,
                "allowed_real_primitives": ["move_right_short"] if real_single_tap else [],
                "input_attempt_count": inputs_sent if real_single_tap else real_inputs_sent,
                "allowed_input_count": inputs_sent if real_single_tap else real_inputs_sent,
                "forbidden_input_count": real_forbidden_input_count,
                "executed_action_count": inputs_sent if real_single_tap else real_inputs_sent,
                "executed_wait_count": 0 if real_single_tap else real_inputs_sent,
                "forbidden_executed_action_count": 0,
                "focus_guard_check_count": (
                    real_focus_guard_check_count
                    if real_focus_guard_check_count is not None
                    else inputs_sent
                    if real_single_tap
                    else real_inputs_sent
                ),
                "focus_guard_pre_input_pass_count": (
                    real_focus_guard_check_count
                    if real_focus_guard_check_count is not None
                    else inputs_sent
                    if real_single_tap
                    else real_inputs_sent
                ),
                "emergency_stop_check_count": (
                    real_emergency_stop_check_count
                    if real_emergency_stop_check_count is not None
                    else inputs_sent
                    if real_single_tap
                    else real_inputs_sent
                ),
                "emergency_stop_pre_input_clear_count": (
                    real_emergency_stop_check_count
                    if real_emergency_stop_check_count is not None
                    else inputs_sent
                    if real_single_tap
                    else real_inputs_sent
                ),
                "rate_limit_enabled": real_wait_only,
                "max_input_count": 1 if real_single_tap else real_inputs_sent,
                "max_input_count_exceeded": False,
                "capture_script": real_capture_script
                if real_wait_only or real_single_tap
                else None,
                "official_screen_only": True,
                "dryrun_task_count": len(dryrun_tasks),
                "dryrun_skill_count": len(dryrun_tasks),
                "dryrun_tasks": dryrun_tasks,
                "manager_dryrun_active": dryrun_orchestration_mode == "wait_only",
                "body_dryrun_active": dryrun_orchestration_mode == "wait_only",
                "requested_actions": requested_actions,
                "executed_actions": requested_actions
                if requested_action_executed or dryrun_executed or real_wait_only or real_single_tap
                else [],
                "captured_frame_count": frame_count,
                "evidence_ids": evidence_ids,
                "pre_input_evidence_ids": [evidence_ids[0]] if real_single_tap else [],
                "post_input_evidence_ids": (
                    [evidence_ids[1]] if real_single_tap and include_post_evidence else []
                ),
                "screenshot_paths": screenshot_paths,
                "screenshot_evidence": [
                    {
                        "evidence_id": evidence_id,
                        "screenshot_path": screenshot_path,
                        "timestamp": f"2026-05-17T12:00:{index:02d}Z",
                        "width": 1,
                        "height": 1,
                        "sha256": "abc123",
                    }
                    for index, (evidence_id, screenshot_path) in enumerate(
                        zip(evidence_ids, screenshot_paths, strict=False)
                    )
                ],
                "autonomous_planner_active": planner_active,
                "manager_orchestration_active": manager_active,
                "body_control_active": body_active,
                "learning_active": learning_active,
                "bridge_active": bridge_active,
                "ocr_active": False,
                "hidden_state_violation_count": hidden_state_violation_count,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    validation_checks = [
        {
            "name": "forbidden_runtime_markers_absent",
            "passed": forbidden_marker_check_passed,
            "severity": "info" if forbidden_marker_check_passed else "error",
            "message": "forbidden runtime marker check",
        },
        {
            "name": "hidden_state_fields_absent",
            "passed": hidden_state_check_passed,
            "severity": "info" if hidden_state_check_passed else "error",
            "message": "hidden-state field check",
        },
    ]
    if include_validation_report:
        (reports_dir / "live_smoke_report_validation.json").write_text(
            json.dumps(
                {
                    "validation_report_version": "1",
                    "created_at": "2026-05-17T12:00:00Z",
                    "source_report_path": str(reports_dir / "live_smoke_report.json"),
                    "expected_frame_count": frame_count,
                    "status": {
                        "passed": validator_passed,
                        "check_count": 10,
                        "error_count": validation_error_count,
                    },
                    "checks": validation_checks,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    return run_dir


def test_review_summary_passes_for_valid_three_frame_run_fixture(tmp_path: Path) -> None:
    run_dir = write_review_fixture(tmp_path)

    summary = create_controlled_live_smoke_review_summary(
        run_dir=run_dir,
        created_at=FIXED_CREATED_AT,
    )

    assert summary.conclusion == "passed"
    assert summary.run_id == "run_12_10b_three_frame_manual"
    assert summary.mode == "official_screen_only"
    assert summary.runtime_mode == "observation_only"
    assert summary.preflight_ok is True
    assert summary.validator_passed is True
    assert summary.no_input_sent is True
    assert summary.actions_requested == 0
    assert summary.inputs_sent == 0
    assert summary.action_logging_mode == "disabled"
    assert summary.stop_reason == "max_frames_reached"
    assert summary.recommended_next_step == PASSED_NEXT_STEP


def test_review_summary_passes_for_valid_thirty_frame_run_fixture(tmp_path: Path) -> None:
    run_dir = write_review_fixture(tmp_path, frame_count=30)

    summary = create_controlled_live_smoke_review_summary(
        run_dir=run_dir,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert summary.conclusion == "passed"
    assert summary.frame_count == 30
    assert summary.captured_frame_count == 30
    assert summary.screenshot_count == 30
    assert summary.evidence_count == 30
    assert summary.min_frame_count == 10
    assert summary.max_frame_count == 30
    assert summary.duration_seconds == 29.0
    assert summary.average_capture_interval_seconds == 1.0
    assert summary.input_action_counters == {"actions_requested": 0, "inputs_sent": 0}


def test_review_summary_fails_when_validator_failed(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        validator_passed=False,
        validation_error_count=1,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "validator did not pass" in summary.failure_reasons
    assert summary.validation_error_count == 1


def test_review_summary_fails_when_no_input_sent_false(tmp_path: Path) -> None:
    run_dir = write_review_fixture(tmp_path, no_input_sent=False)

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "report does not confirm no_input_sent=true" in summary.failure_reasons


def test_review_summary_fails_when_actions_requested_nonzero(tmp_path: Path) -> None:
    run_dir = write_review_fixture(tmp_path, actions_requested=1)

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "actions_requested is not zero" in summary.failure_reasons


def test_review_summary_passes_for_wait_only_noop_actions(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=30,
        action_logging_mode="wait_only_noop",
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "passed"
    assert summary.action_logging_mode == "wait_only_noop"
    assert summary.actions_requested == 30
    assert summary.inputs_sent == 0
    assert summary.allowed_action_intent_count == 30
    assert summary.forbidden_action_intent_count == 0
    assert summary.executed_action_count == 0


def test_review_summary_passes_for_dryrun_wait_only_task(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=1,
        dryrun_orchestration_mode="wait_only",
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "passed"
    assert summary.action_logging_mode == "disabled"
    assert summary.dryrun_orchestration_mode == "wait_only"
    assert summary.dryrun_task_count == 1
    assert summary.dryrun_skill_count == 1
    assert summary.allowed_dryrun_task_count == 1
    assert summary.forbidden_dryrun_task_count == 0
    assert summary.allowed_dryrun_action_intent_count == 1
    assert summary.forbidden_dryrun_action_intent_count == 0
    assert summary.manager_dryrun_active is True
    assert summary.body_dryrun_active is True
    assert summary.manager_active is False
    assert summary.body_active is False
    assert summary.allowed_action_intent_count == 1
    assert summary.forbidden_action_intent_count == 0
    assert summary.executed_action_count == 0


def test_review_summary_passes_for_real_wait_only_noop_inputs(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        real_input_mode="wait_only_noop",
        real_inputs_sent=15,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "passed"
    assert summary.real_input_mode == "wait_only_noop"
    assert summary.real_wait_only_active is True
    assert summary.actions_requested == 15
    assert summary.inputs_sent == 15
    assert summary.no_input_sent is False
    assert summary.allowed_input_count == 15
    assert summary.forbidden_input_count == 0
    assert summary.executed_action_count == 15
    assert summary.executed_wait_count == 15
    assert summary.focus_guard_check_count == 15
    assert summary.emergency_stop_check_count == 15
    assert summary.rate_limit_enabled is True
    assert summary.capture_script == "./scripts/capture_active_window_ppm.sh"


def test_review_summary_fails_real_wait_only_with_missing_focus_check(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        real_input_mode="wait_only_noop",
        real_inputs_sent=15,
        real_focus_guard_check_count=14,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "focus_guard_check_count is below inputs_sent" in summary.failure_reasons


def test_review_summary_fails_real_wait_only_with_old_capture_script(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        real_input_mode="wait_only_noop",
        real_inputs_sent=15,
        real_capture_script="./scripts/capture_one_frame_ppm.sh",
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "capture_script is not the active-window script" in summary.failure_reasons


def test_review_summary_passes_for_single_directional_tap(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "passed"
    assert summary.real_input_mode == "single_directional_tap"
    assert summary.allowed_real_primitives == ("move_right_short",)
    assert summary.requested_action_names == ("move_right_short",)
    assert summary.executed_action_names == ("move_right_short",)
    assert summary.inputs_sent == 1
    assert summary.max_input_count == 1
    assert summary.pre_input_evidence_count == 1
    assert summary.post_input_evidence_count == 1
    assert summary.focus_guard_check_count == 1
    assert summary.emergency_stop_check_count == 1
    assert summary.forbidden_input_count == 0
    assert summary.hidden_state_violation_count == 0
    assert summary.planner_active is False
    assert summary.manager_active is False
    assert summary.body_active is False
    assert summary.bridge_active is False
    assert summary.ocr_active is False
    assert summary.learning_active is False
    assert summary.automated_review_scope == "mechanical"
    assert summary.visual_review_required is True
    assert summary.visual_review_status == "not_performed"
    assert summary.requires_manual_visual_review is True
    assert summary.recommended_next_step == SINGLE_TAP_MECHANICAL_NEXT_STEP


def test_review_summary_passes_for_single_directional_tap_without_preflight_artifact(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
        include_preflight_report=False,
        include_pipeline_summary=False,
    )

    summary = create_controlled_live_smoke_review_summary(
        run_dir=run_dir,
        min_frame_count=2,
        max_frame_count=2,
    )

    assert summary.conclusion == "passed"
    assert summary.preflight_ok is True
    assert summary.validator_passed is True
    assert summary.real_input_mode == "single_directional_tap"
    assert summary.inputs_sent == 1
    assert summary.visual_review_required is True


def test_review_summary_fails_when_validation_report_is_missing(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
        include_validation_report=False,
        include_preflight_report=False,
        include_pipeline_summary=False,
    )

    with pytest.raises(ValueError, match="live_smoke_report_validation.json"):
        create_controlled_live_smoke_review_summary(run_dir=run_dir)


def test_review_summary_fails_single_directional_tap_when_validation_failed(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        validator_passed=False,
        validation_error_count=1,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
        include_preflight_report=False,
        include_pipeline_summary=False,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "validator did not pass" in summary.failure_reasons


def test_review_summary_fails_single_directional_tap_pre_post_dimension_mismatch(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
    )
    report_path = run_dir / "reports" / "live_smoke_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["screenshot_evidence"][0]["width"] = 1355
    payload["screenshot_evidence"][0]["height"] = 975
    payload["screenshot_evidence"][1]["width"] = 611
    payload["screenshot_evidence"][1]["height"] = 341
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert (
        "pre/post screenshots do not match target window dimensions; "
        "possible focus steal or OS dialog."
    ) in summary.failure_reasons


def test_review_summary_fails_single_directional_tap_missing_post_evidence(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
        include_post_evidence=False,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "post-input evidence is missing" in summary.failure_reasons


def test_review_summary_fails_single_directional_tap_with_more_than_one_input(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=2,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "input_attempt_count is not one" in summary.failure_reasons
    assert "inputs_sent is not one" in summary.failure_reasons


def test_review_summary_fails_single_directional_tap_missing_gate_checks(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
        real_focus_guard_check_count=0,
        real_emergency_stop_check_count=0,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "focus_guard_check_count is not one" in summary.failure_reasons
    assert "emergency_stop_check_count is not one" in summary.failure_reasons


def test_review_summary_fails_single_directional_tap_hidden_state_violation(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
        hidden_state_violation_count=1,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "hidden_state_violation_count is not zero" in summary.failure_reasons


@pytest.mark.parametrize("action", ["wait", "confirm", "cancel", "open_menu"])
def test_review_summary_fails_single_directional_tap_wrong_action(
    tmp_path: Path,
    action: str,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=2,
        real_input_mode="single_directional_tap",
        real_inputs_sent=1,
        single_action=action,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "forbidden action intents are present" in summary.failure_reasons


@pytest.mark.parametrize("action", ["move_up_short", "confirm", "cancel", "open_menu"])
def test_review_summary_fails_dryrun_wait_only_with_forbidden_action(
    tmp_path: Path,
    action: str,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=1,
        dryrun_orchestration_mode="wait_only",
        dryrun_action=action,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert summary.forbidden_dryrun_task_count == 1
    assert summary.forbidden_dryrun_action_intent_count == 1
    assert "forbidden dryrun tasks are present" in summary.failure_reasons
    assert "forbidden dryrun action intents are present" in summary.failure_reasons


def test_review_summary_fails_dryrun_wait_only_with_executed_action(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=1,
        dryrun_orchestration_mode="wait_only",
        dryrun_executed=True,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert summary.executed_action_count == 1
    assert "executed action intents are present" in summary.failure_reasons


def test_review_summary_fails_dryrun_wait_only_with_inputs_sent(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=1,
        inputs_sent=1,
        no_input_sent=False,
        dryrun_orchestration_mode="wait_only",
        dryrun_input_sent=True,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "report does not confirm no_input_sent=true" in summary.failure_reasons
    assert "inputs_sent is not zero" in summary.failure_reasons
    assert "forbidden dryrun action intents are present" in summary.failure_reasons


def test_review_summary_fails_dryrun_wait_only_with_planner_active(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=1,
        dryrun_orchestration_mode="wait_only",
        planner_active=True,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "planner_active is true" in summary.failure_reasons


def test_review_summary_fails_wait_only_noop_with_forbidden_action(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=30,
        action_logging_mode="wait_only_noop",
        requested_action="confirm",
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert summary.forbidden_action_intent_count == 30
    assert "forbidden action intents are present" in summary.failure_reasons


def test_review_summary_fails_wait_only_noop_with_inputs_sent(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=30,
        inputs_sent=1,
        action_logging_mode="wait_only_noop",
        requested_action_input_sent=True,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "inputs_sent is not zero" in summary.failure_reasons
    assert "forbidden action intents are present" in summary.failure_reasons


def test_review_summary_fails_wait_only_noop_with_executed_action(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        actions_requested=30,
        action_logging_mode="wait_only_noop",
        requested_action_executed=True,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert summary.executed_action_count == 30
    assert "executed action intents are present" in summary.failure_reasons


def test_review_summary_fails_when_hidden_state_check_failed(tmp_path: Path) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        validator_passed=False,
        validation_error_count=1,
        hidden_state_check_passed=False,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert summary.hidden_state_fields_absent is False
    assert "hidden-state field check failed" in summary.failure_reasons


def test_review_summary_fails_when_forbidden_runtime_marker_check_failed(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        validator_passed=False,
        validation_error_count=1,
        forbidden_marker_check_passed=False,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert summary.forbidden_runtime_markers_absent is False
    assert "forbidden runtime marker check failed" in summary.failure_reasons


def test_review_summary_fails_when_planner_manager_body_or_learning_active(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        planner_active=True,
        manager_active=True,
        body_active=True,
        learning_active=True,
        bridge_active=True,
    )

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.conclusion == "failed"
    assert "planner_active is true" in summary.failure_reasons
    assert "manager_active is true" in summary.failure_reasons
    assert "body_active is true" in summary.failure_reasons
    assert "learning_active is true" in summary.failure_reasons
    assert "bridge_active is true" in summary.failure_reasons


def test_review_summary_fails_when_count_mismatch_between_frames_screenshots_evidence(
    tmp_path: Path,
) -> None:
    run_dir = write_review_fixture(
        tmp_path,
        frame_count=30,
        screenshot_count_delta=-1,
        evidence_count_delta=-1,
    )

    summary = create_controlled_live_smoke_review_summary(
        run_dir=run_dir,
        min_frame_count=10,
        max_frame_count=30,
    )

    assert summary.conclusion == "failed"
    assert "screenshot_count does not match captured_frame_count" in summary.failure_reasons
    assert "evidence_count does not match captured_frame_count" in summary.failure_reasons


def test_review_summary_counts_screenshots_and_evidence(tmp_path: Path) -> None:
    run_dir = write_review_fixture(tmp_path)

    summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)

    assert summary.captured_frame_count == 3
    assert summary.screenshot_count == 3
    assert summary.evidence_count == 3


def test_review_summary_writes_deterministic_json(tmp_path: Path) -> None:
    summary = create_controlled_live_smoke_review_summary(
        run_dir=write_review_fixture(tmp_path),
        created_at=FIXED_CREATED_AT,
    )

    path = write_controlled_live_smoke_review_summary(summary)

    assert json.loads(path.read_text(encoding="utf-8")) == json.loads(
        summary.to_deterministic_json()
    )
    assert summary.to_deterministic_json() == summary.to_deterministic_json()


def test_review_summary_refuses_overwrite_by_default(tmp_path: Path) -> None:
    summary = create_controlled_live_smoke_review_summary(run_dir=write_review_fixture(tmp_path))
    write_controlled_live_smoke_review_summary(summary)

    with pytest.raises(FileExistsError):
        write_controlled_live_smoke_review_summary(summary)


def test_manual_visual_review_recorder_records_passed_status_to_new_output_json(
    tmp_path: Path,
) -> None:
    review_path = write_single_tap_review_json(tmp_path)
    output = tmp_path / "manual_review.json"

    payload = record_controlled_live_smoke_manual_visual_review(
        review_path=review_path,
        status="passed",
    )
    write_controlled_live_smoke_manual_visual_review(payload, output)

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["visual_review_status"] == "passed"
    assert written["visual_review_timestamp_utc"].endswith("Z")


def test_manual_visual_review_recorder_records_failed_status_to_new_output_json(
    tmp_path: Path,
) -> None:
    review_path = write_single_tap_review_json(tmp_path)
    output = tmp_path / "manual_review_failed.json"

    payload = record_controlled_live_smoke_manual_visual_review(
        review_path=review_path,
        status="failed",
    )
    write_controlled_live_smoke_manual_visual_review(payload, output)

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["visual_review_status"] == "failed"


def test_manual_visual_review_recorder_preserves_existing_mechanical_review_fields(
    tmp_path: Path,
) -> None:
    review_path = write_single_tap_review_json(tmp_path)
    before = json.loads(review_path.read_text(encoding="utf-8"))

    after = record_controlled_live_smoke_manual_visual_review(
        review_path=review_path,
        status="passed",
    )

    for key in (
        "run_id",
        "conclusion",
        "failure_reasons",
        "validator_passed",
        "real_input_mode",
        "inputs_sent",
        "executed_action_count",
    ):
        assert after[key] == before[key]


def test_manual_visual_review_recorder_writes_notes_and_reviewer(tmp_path: Path) -> None:
    review_path = write_single_tap_review_json(tmp_path)

    payload = record_controlled_live_smoke_manual_visual_review(
        review_path=review_path,
        status="passed",
        notes="same game window; no interactive prompt",
        reviewer="human-reviewer",
    )

    assert payload["visual_review_notes"] == "same game window; no interactive prompt"
    assert payload["visual_reviewer"] == "human-reviewer"


def test_manual_visual_review_recorder_accepts_utc_timestamp(tmp_path: Path) -> None:
    review_path = write_single_tap_review_json(tmp_path)

    payload = record_controlled_live_smoke_manual_visual_review(
        review_path=review_path,
        status="passed",
        timestamp_utc=FIXED_CREATED_AT,
    )

    assert payload["visual_review_timestamp_utc"] == "2026-05-17T12:00:00Z"


def test_manual_visual_review_recorder_rejects_invalid_status(tmp_path: Path) -> None:
    review_path = write_single_tap_review_json(tmp_path)

    with pytest.raises(ValueError, match="passed or failed"):
        record_controlled_live_smoke_manual_visual_review(
            review_path=review_path,
            status="unknown",  # type: ignore[arg-type]
        )


def test_manual_visual_review_recorder_rejects_missing_review_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        record_controlled_live_smoke_manual_visual_review(
            review_path=tmp_path / "missing.json",
            status="failed",
        )


def test_manual_visual_review_recorder_rejects_malformed_review_json(tmp_path: Path) -> None:
    review_path = tmp_path / "malformed.json"
    review_path.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid controlled smoke review artifact"):
        record_controlled_live_smoke_manual_visual_review(
            review_path=review_path,
            status="failed",
        )


def test_manual_visual_review_recorder_rejects_existing_output_without_overwrite(
    tmp_path: Path,
) -> None:
    review_path = write_single_tap_review_json(tmp_path)
    output = tmp_path / "manual_review.json"
    output.write_text("{}", encoding="utf-8")
    payload = record_controlled_live_smoke_manual_visual_review(
        review_path=review_path,
        status="passed",
    )

    with pytest.raises(FileExistsError, match="already exists"):
        write_controlled_live_smoke_manual_visual_review(payload, output)


def test_manual_visual_review_recorder_rejects_passed_when_mechanical_conclusion_failed(
    tmp_path: Path,
) -> None:
    review_path = write_single_tap_review_json(
        tmp_path,
        updates={"conclusion": "failed", "failure_reasons": ["synthetic failure"]},
    )

    with pytest.raises(ValueError, match="mechanical review conclusion failed"):
        record_controlled_live_smoke_manual_visual_review(
            review_path=review_path,
            status="passed",
        )


def test_manual_visual_review_recorder_allows_failed_when_mechanical_conclusion_failed(
    tmp_path: Path,
) -> None:
    review_path = write_single_tap_review_json(
        tmp_path,
        updates={"conclusion": "failed", "failure_reasons": ["synthetic failure"]},
    )

    payload = record_controlled_live_smoke_manual_visual_review(
        review_path=review_path,
        status="failed",
    )

    assert payload["conclusion"] == "failed"
    assert payload["visual_review_status"] == "failed"


def test_cli_manual_visual_review_rejects_output_and_in_place_together(tmp_path: Path) -> None:
    review_path = write_single_tap_review_json(tmp_path)
    output = tmp_path / "manual_review.json"

    result = CliRunner().invoke(
        app,
        [
            "controlled-live-smoke-record-manual-review",
            "--review",
            str(review_path),
            "--status",
            "passed",
            "--output",
            str(output),
            "--in-place",
        ],
    )

    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_cli_manual_visual_review_requires_output_or_in_place(tmp_path: Path) -> None:
    review_path = write_single_tap_review_json(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "controlled-live-smoke-record-manual-review",
            "--review",
            str(review_path),
            "--status",
            "passed",
        ],
    )

    assert result.exit_code != 0
    assert "provide --output or --in-place" in result.output


def test_cli_manual_visual_review_writes_output(tmp_path: Path) -> None:
    review_path = write_single_tap_review_json(tmp_path)
    output = tmp_path / "manual_review.json"

    result = CliRunner().invoke(
        app,
        [
            "controlled-live-smoke-record-manual-review",
            "--review",
            str(review_path),
            "--status",
            "passed",
            "--notes",
            "same game window",
            "--reviewer",
            "human",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["visual_review_status"] == "passed"
    assert payload["visual_review_notes"] == "same game window"
    assert payload["visual_reviewer"] == "human"


def test_cli_help_includes_controlled_live_smoke_review() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "controlled-live-smoke-review" in result.output
    assert "controlled-live-smoke-record-manual-review" in result.output


def test_cli_review_help_includes_longer_observation_frame_bounds() -> None:
    result = CliRunner().invoke(app, ["controlled-live-smoke-review", "--help"])

    assert result.exit_code == 0
    assert "--min-frame-count" in result.output
    assert "--max-frame-count" in result.output


def test_source_scan_blocks_runtime_input_bridge_planner_manager_body_rl_ocr_imports() -> None:
    source = Path(review_module.__file__).read_text(encoding="utf-8")

    forbidden_terms = (
        "fh_agent.game",
        "fh_agent.bridge",
        "keyboard",
        "pyautogui",
        "InputExecutor",
        "input_executor",
        "fh_agent.planner",
        "llm_client",
        "fh_agent.manager",
        "task_manager",
        "orchestrator",
        "fh_agent.body",
        "fh_agent.rl",
        "torch",
        "stable_baselines3",
        "PaddleOCR",
        "paddleocr",
        "observation_builder",
        "offline_processor",
    )
    for term in forbidden_terms:
        assert term not in source


def write_single_tap_review_json(
    tmp_path: Path,
    *,
    updates: dict[str, object] | None = None,
) -> Path:
    summary = create_controlled_live_smoke_review_summary(
        run_dir=write_review_fixture(
            tmp_path,
            frame_count=2,
            real_input_mode="single_directional_tap",
            real_inputs_sent=1,
            include_preflight_report=False,
            include_pipeline_summary=False,
        ),
        min_frame_count=2,
        max_frame_count=2,
        created_at=FIXED_CREATED_AT,
    )
    path = write_controlled_live_smoke_review_summary(summary, overwrite=True)
    if updates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.update(updates)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path
