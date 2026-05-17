import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.evals.controlled_live_smoke_review as review_module
from fh_agent.cli import app
from fh_agent.evals.controlled_live_smoke_review import (
    PASSED_NEXT_STEP,
    create_controlled_live_smoke_review_summary,
    write_controlled_live_smoke_review_summary,
)

FIXED_CREATED_AT = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)


def write_review_fixture(
    tmp_path: Path,
    *,
    frame_count: int = 3,
    validator_passed: bool = True,
    validation_error_count: int = 0,
    no_input_sent: bool = True,
    actions_requested: int = 0,
    inputs_sent: int = 0,
    action_logging_mode: str = "disabled",
    requested_action: str = "wait",
    requested_action_executed: bool = False,
    requested_action_input_sent: bool = False,
    planner_active: bool = False,
    manager_active: bool = False,
    body_active: bool = False,
    learning_active: bool = False,
    bridge_active: bool = False,
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
                "allow_real_input": False,
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
                "requested_actions": requested_actions,
                "executed_actions": requested_actions if requested_action_executed else [],
                "captured_frame_count": frame_count,
                "evidence_ids": evidence_ids,
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


def test_cli_help_includes_controlled_live_smoke_review() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "controlled-live-smoke-review" in result.output


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
