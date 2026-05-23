import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.evals.controlled_live_smoke_validator as validator_module
from fh_agent.cli import app
from fh_agent.evals.controlled_live_smoke_validator import (
    validate_controlled_live_smoke_artifacts,
    write_controlled_live_smoke_validation_report,
)

FIXED_CREATED_AT = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)


def make_report_payload(tmp_path: Path, *, frame_count: int = 1) -> dict[str, object]:
    screenshot_paths: list[Path] = []
    screenshot_evidence: list[dict[str, object]] = []
    for index in range(frame_count):
        evidence_id = f"evidence-{index}"
        screenshot_path = tmp_path / "runs" / "run_0001" / "screenshots" / f"{evidence_id}.ppm"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(b"P6\n1 1\n255\nabc")
        screenshot_paths.append(screenshot_path)
        screenshot_evidence.append(
            {
                "evidence_id": evidence_id,
                "screenshot_path": str(screenshot_path),
                "timestamp": "2026-05-16T12:00:00Z",
                "width": 1,
                "height": 1,
                "sha256": "abc123",
            }
        )
    return {
        "report_version": "1",
        "run_id": "run_0001",
        "created_at": "2026-05-16T12:00:00Z",
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
            "actions_requested": 0,
        },
        "event_count": 4,
        "runtime_mode": "observation_only",
        "no_input_sent": True,
        "inputs_sent": 0,
        "action_logging_mode": "disabled",
        "requested_actions": [],
        "executed_actions": [],
        "captured_frame_count": frame_count,
        "evidence_ids": [f"evidence-{index}" for index in range(frame_count)],
        "screenshot_paths": [str(path) for path in screenshot_paths],
        "screenshot_evidence": screenshot_evidence,
        "autonomous_planner_active": False,
        "manager_orchestration_active": False,
        "body_control_active": False,
        "learning_active": False,
    }


def add_wait_only_noop_actions(
    payload: dict[str, object],
    *,
    action: str = "wait",
    executed: bool = False,
    input_sent: bool = False,
) -> dict[str, object]:
    frame_count = int(payload["captured_frame_count"])
    actions = [
        {
            "action": action,
            "requested": True,
            "executed": executed,
            "input_sent": input_sent,
            "reason": "noop_action_logging",
            "frame_index": index,
        }
        for index in range(frame_count)
    ]
    payload["action_logging_mode"] = "wait_only_noop"
    payload["inputs_sent"] = 1 if input_sent else 0
    payload["requested_actions"] = actions
    payload["executed_actions"] = actions if executed else []
    payload["status"]["actions_requested"] = len(actions)  # type: ignore[index]
    return payload


def add_dryrun_wait_only_task(
    payload: dict[str, object],
    *,
    action: str = "wait",
    selected_skill: str = "wait",
    executed: bool = False,
    input_sent: bool = False,
    planner_active: bool = False,
) -> dict[str, object]:
    action_intent = {
        "action": action,
        "requested": True,
        "executed": executed,
        "input_sent": input_sent,
        "reason": "dryrun_orchestration_wait_only",
        "frame_index": 0,
    }
    payload["dryrun_orchestration_mode"] = "wait_only"
    payload["manager_dryrun_active"] = True
    payload["body_dryrun_active"] = True
    payload["dryrun_task_count"] = 1
    payload["dryrun_skill_count"] = 1
    payload["dryrun_tasks"] = [
        {
            "task_id": "dryrun-wait-0",
            "static_goal": "maintain_observation_without_input",
            "selected_skill": selected_skill,
            "action_intent": action_intent,
        }
    ]
    payload["requested_actions"] = [action_intent]
    payload["executed_actions"] = [action_intent] if executed else []
    payload["inputs_sent"] = 1 if input_sent else 0
    payload["no_input_sent"] = not input_sent
    payload["autonomous_planner_active"] = planner_active
    payload["status"]["actions_requested"] = 1  # type: ignore[index]
    return payload


def write_report(tmp_path: Path, payload: dict[str, object] | None = None) -> Path:
    path = tmp_path / "controlled_report.json"
    path.write_text(
        json.dumps(payload or make_report_payload(tmp_path), sort_keys=True),
        encoding="utf-8",
    )
    return path


def check_status(report_path: Path, *, expected_frame_count: int = 1):
    return validate_controlled_live_smoke_artifacts(
        report_path=report_path,
        expected_frame_count=expected_frame_count,
        created_at=FIXED_CREATED_AT,
    )


def test_validates_clean_one_frame_report(tmp_path: Path) -> None:
    validation = check_status(write_report(tmp_path))

    assert validation.status.passed is True
    assert validation.status.error_count == 0


def test_validator_accepts_run_specific_screenshot_path(tmp_path: Path) -> None:
    report_path = write_report(tmp_path)

    validation = check_status(report_path)

    assert validation.status.passed is True
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert Path(payload["screenshot_paths"][0]).parent == (
        tmp_path / "runs" / "run_0001" / "screenshots"
    )


def test_rejects_report_with_no_input_sent_false(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path)
    payload["no_input_sent"] = False

    validation = check_status(write_report(tmp_path, payload))

    assert validation.status.passed is False
    assert any(check.name == "no_input_sent" and not check.passed for check in validation.checks)


def test_rejects_report_with_non_observation_runtime_mode(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path)
    payload["runtime_mode"] = "interactive"

    validation = check_status(write_report(tmp_path, payload))

    assert validation.status.passed is False
    assert any(
        check.name == "runtime_mode_observation_only" and not check.passed
        for check in validation.checks
    )


def test_rejects_report_with_more_than_one_frame_by_default(tmp_path: Path) -> None:
    validation = check_status(write_report(tmp_path, make_report_payload(tmp_path, frame_count=2)))

    assert validation.status.passed is False
    assert any(
        check.name == "captured_frame_count" and not check.passed for check in validation.checks
    )


def test_accepts_custom_expected_frame_count_when_explicit(tmp_path: Path) -> None:
    validation = check_status(
        write_report(tmp_path, make_report_payload(tmp_path, frame_count=2)),
        expected_frame_count=2,
    )

    assert validation.status.passed is True


def test_validator_accepts_expected_frame_count_three(tmp_path: Path) -> None:
    validation = check_status(
        write_report(tmp_path, make_report_payload(tmp_path, frame_count=3)),
        expected_frame_count=3,
    )

    assert validation.status.passed is True


def test_validator_accepts_frame_count_range_for_longer_observation_smoke(tmp_path: Path) -> None:
    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, make_report_payload(tmp_path, frame_count=30)),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is True


def test_validator_rejects_actions_requested_nonzero(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path, frame_count=30)
    payload["status"]["actions_requested"] = 1

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "actions_requested_zero" and not check.passed for check in validation.checks
    )


def test_normal_observation_only_still_requires_zero_actions_requested(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path, frame_count=30)
    payload["action_logging_mode"] = "disabled"
    payload["status"]["actions_requested"] = 1
    payload["requested_actions"] = []

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "actions_requested_zero" and not check.passed for check in validation.checks
    )


def test_wait_only_noop_with_wait_intents_and_no_inputs_passes(tmp_path: Path) -> None:
    payload = add_wait_only_noop_actions(make_report_payload(tmp_path, frame_count=30))

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is True
    assert any(
        check.name == "wait_only_noop_requested_actions_safe" and check.passed
        for check in validation.checks
    )


@pytest.mark.parametrize("action", ["move_up_short", "confirm", "cancel", "open_menu"])
def test_wait_only_noop_rejects_non_wait_actions(tmp_path: Path, action: str) -> None:
    payload = add_wait_only_noop_actions(
        make_report_payload(tmp_path, frame_count=30),
        action=action,
    )

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "wait_only_noop_requested_actions_safe" and not check.passed
        for check in validation.checks
    )


def test_wait_only_noop_rejects_inputs_sent(tmp_path: Path) -> None:
    payload = add_wait_only_noop_actions(
        make_report_payload(tmp_path, frame_count=30),
        input_sent=True,
    )

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(check.name == "inputs_sent_zero" and not check.passed for check in validation.checks)
    assert any(
        check.name == "wait_only_noop_requested_actions_safe" and not check.passed
        for check in validation.checks
    )


def test_wait_only_noop_rejects_executed_true(tmp_path: Path) -> None:
    payload = add_wait_only_noop_actions(
        make_report_payload(tmp_path, frame_count=30),
        executed=True,
    )

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "executed_actions_empty" and not check.passed for check in validation.checks
    )
    assert any(
        check.name == "wait_only_noop_requested_actions_safe" and not check.passed
        for check in validation.checks
    )


def test_dryrun_wait_only_with_wait_task_and_no_inputs_passes(tmp_path: Path) -> None:
    payload = add_dryrun_wait_only_task(make_report_payload(tmp_path, frame_count=30))

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is True
    assert any(
        check.name == "dryrun_wait_only_tasks_safe" and check.passed for check in validation.checks
    )
    assert any(
        check.name == "dryrun_wait_only_requested_actions_safe" and check.passed
        for check in validation.checks
    )


@pytest.mark.parametrize("action", ["move_up_short", "confirm", "cancel", "open_menu"])
def test_dryrun_wait_only_rejects_non_wait_actions(tmp_path: Path, action: str) -> None:
    payload = add_dryrun_wait_only_task(
        make_report_payload(tmp_path, frame_count=30),
        action=action,
    )

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "dryrun_wait_only_tasks_safe" and not check.passed
        for check in validation.checks
    )
    assert any(
        check.name == "dryrun_wait_only_requested_actions_safe" and not check.passed
        for check in validation.checks
    )


def test_dryrun_wait_only_rejects_non_wait_skill(tmp_path: Path) -> None:
    payload = add_dryrun_wait_only_task(
        make_report_payload(tmp_path, frame_count=30),
        selected_skill="confirm",
    )

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "dryrun_wait_only_tasks_safe" and not check.passed
        for check in validation.checks
    )


def test_dryrun_wait_only_rejects_executed_true(tmp_path: Path) -> None:
    payload = add_dryrun_wait_only_task(
        make_report_payload(tmp_path, frame_count=30),
        executed=True,
    )

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "executed_actions_empty" and not check.passed for check in validation.checks
    )
    assert any(
        check.name == "dryrun_wait_only_tasks_safe" and not check.passed
        for check in validation.checks
    )


def test_dryrun_wait_only_rejects_inputs_sent(tmp_path: Path) -> None:
    payload = add_dryrun_wait_only_task(
        make_report_payload(tmp_path, frame_count=30),
        input_sent=True,
    )

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(check.name == "inputs_sent_zero" and not check.passed for check in validation.checks)
    assert any(check.name == "no_input_sent" and not check.passed for check in validation.checks)
    assert any(
        check.name == "dryrun_wait_only_tasks_safe" and not check.passed
        for check in validation.checks
    )


def test_dryrun_wait_only_rejects_planner_active(tmp_path: Path) -> None:
    payload = add_dryrun_wait_only_task(
        make_report_payload(tmp_path, frame_count=30),
        planner_active=True,
    )

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "autonomy_flags_inactive" and not check.passed for check in validation.checks
    )


def test_validator_rejects_count_mismatch_between_frames_screenshots_evidence(
    tmp_path: Path,
) -> None:
    payload = make_report_payload(tmp_path, frame_count=30)
    payload["screenshot_paths"] = payload["screenshot_paths"][:-1]
    payload["evidence_ids"] = payload["evidence_ids"][:-1]

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "screenshot_count_matches_frame_count" and not check.passed
        for check in validation.checks
    )
    assert any(
        check.name == "evidence_count_matches_frame_count" and not check.passed
        for check in validation.checks
    )


def test_validator_rejects_active_autonomy_flags(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path, frame_count=30)
    payload["autonomous_planner_active"] = True
    payload["manager_orchestration_active"] = True
    payload["body_control_active"] = True
    payload["learning_active"] = True
    payload["bridge_active"] = True

    validation = validate_controlled_live_smoke_artifacts(
        report_path=write_report(tmp_path, payload),
        expected_frame_count=None,
        min_frame_count=10,
        max_frame_count=30,
        created_at=FIXED_CREATED_AT,
    )

    assert validation.status.passed is False
    assert any(
        check.name == "autonomy_flags_inactive" and not check.passed for check in validation.checks
    )


def test_rejects_missing_screenshot_file(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path)
    for path in payload["screenshot_paths"]:
        Path(str(path)).unlink()

    validation = check_status(write_report(tmp_path, payload))

    assert validation.status.passed is False
    assert any(
        check.name == "screenshot_paths_exist" and not check.passed for check in validation.checks
    )


def test_rejects_missing_evidence_id(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path)
    payload["evidence_ids"] = []

    validation = check_status(write_report(tmp_path, payload))

    assert validation.status.passed is False
    assert any(
        check.name == "evidence_ids_present" and not check.passed for check in validation.checks
    )


def test_rejects_runtime_action_or_keypress_markers(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path)
    payload["unexpected_note"] = "move_up_short movement wait keypress"

    validation = check_status(write_report(tmp_path, payload))

    assert validation.status.passed is False
    assert any(
        check.name == "forbidden_runtime_markers_absent" and not check.passed
        for check in validation.checks
    )


def test_rejects_planner_manager_body_bridge_rl_markers(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path)
    payload["unexpected_note"] = "planner manager body bridge rl torch stable_baselines3"

    validation = check_status(write_report(tmp_path, payload))

    assert validation.status.passed is False
    assert any(
        check.name == "forbidden_runtime_markers_absent" and not check.passed
        for check in validation.checks
    )


def test_rejects_hidden_state_fields_recursively(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path)
    payload["nested"] = {"game_switches": {"secret": True}, "event_name": "hidden"}

    validation = check_status(write_report(tmp_path, payload))

    assert validation.status.passed is False
    assert any(
        check.name == "hidden_state_fields_absent" and not check.passed
        for check in validation.checks
    )


def test_writes_deterministic_validation_report(tmp_path: Path) -> None:
    validation = check_status(write_report(tmp_path))
    output = tmp_path / "validation.json"

    write_controlled_live_smoke_validation_report(validation, output)

    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        validation.to_deterministic_json()
    )
    assert validation.to_deterministic_json() == validation.to_deterministic_json()


def test_refuses_to_overwrite_existing_validation_report_by_default(tmp_path: Path) -> None:
    validation = check_status(write_report(tmp_path))
    output = tmp_path / "validation.json"
    write_controlled_live_smoke_validation_report(validation, output)

    with pytest.raises(FileExistsError):
        write_controlled_live_smoke_validation_report(validation, output)


def test_can_overwrite_when_explicitly_requested(tmp_path: Path) -> None:
    validation = check_status(write_report(tmp_path))
    output = tmp_path / "validation.json"
    output.write_text("old\n", encoding="utf-8")

    write_controlled_live_smoke_validation_report(validation, output, overwrite=True)

    assert json.loads(output.read_text(encoding="utf-8"))["status"]["passed"] is True


def test_cli_help_includes_controlled_live_smoke_validate() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "controlled-live-smoke-validate" in result.output


def test_cli_validation_failure_returns_nonzero(tmp_path: Path) -> None:
    payload = make_report_payload(tmp_path)
    payload["no_input_sent"] = False
    report_path = write_report(tmp_path, payload)

    result = CliRunner().invoke(
        app,
        [
            "controlled-live-smoke-validate",
            "--report",
            str(report_path),
            "--output",
            str(tmp_path / "validation.json"),
        ],
    )

    assert result.exit_code != 0
    assert "validation failed" in result.output


def test_source_scan_blocks_live_runtime_imports() -> None:
    source = Path(validator_module.__file__).read_text(encoding="utf-8")

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
