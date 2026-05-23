import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fh_agent.cli import app
from fh_agent.evals.controlled_live_smoke_stability_review import (
    create_controlled_live_smoke_stability_review,
    write_controlled_live_smoke_stability_review,
)

FIXED_CREATED_AT = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)


def write_review(
    tmp_path: Path,
    run_id: str,
    *,
    conclusion: str = "passed",
    frame_count: int = 30,
    action_logging_mode: str = "disabled",
    dryrun_orchestration_mode: str = "disabled",
    dryrun_task_count: int = 0,
    dryrun_skill_count: int = 0,
    allowed_dryrun_task_count: int = 0,
    forbidden_dryrun_task_count: int = 0,
    allowed_dryrun_action_intent_count: int = 0,
    forbidden_dryrun_action_intent_count: int = 0,
    manager_dryrun_active: bool = False,
    body_dryrun_active: bool = False,
    actions_requested: int = 0,
    allowed_action_intent_count: int = 0,
    forbidden_action_intent_count: int = 0,
    executed_action_count: int = 0,
    inputs_sent: int = 0,
    no_input_sent: bool = True,
    hidden_state_fields_absent: bool = True,
    forbidden_runtime_markers_absent: bool = True,
    planner_active: bool = False,
    manager_active: bool = False,
    body_active: bool = False,
    bridge_active: bool = False,
    learning_active: bool = False,
    validator_passed: bool = True,
    validation_error_count: int = 0,
    stop_reason: str = "max_frames_reached",
) -> Path:
    reports_dir = tmp_path / "runs" / run_id / "reports"
    reports_dir.mkdir(parents=True)
    path = reports_dir / "controlled_live_smoke_review.json"
    path.write_text(
        json.dumps(
            {
                "review_summary_version": "1",
                "created_at": "2026-05-17T12:00:00Z",
                "run_id": run_id,
                "mode": "official_screen_only",
                "runtime_mode": "observation_only",
                "preflight_ok": True,
                "validator_passed": validator_passed,
                "validation_error_count": validation_error_count,
                "frame_count": frame_count,
                "captured_frame_count": frame_count,
                "min_frame_count": 30,
                "max_frame_count": 30,
                "screenshot_count": frame_count,
                "evidence_count": frame_count,
                "duration_seconds": 29.0,
                "average_capture_interval_seconds": 1.0,
                "action_logging_mode": action_logging_mode,
                "dryrun_orchestration_mode": dryrun_orchestration_mode,
                "dryrun_task_count": dryrun_task_count,
                "dryrun_skill_count": dryrun_skill_count,
                "allowed_dryrun_task_count": allowed_dryrun_task_count,
                "forbidden_dryrun_task_count": forbidden_dryrun_task_count,
                "allowed_dryrun_action_intent_count": allowed_dryrun_action_intent_count,
                "forbidden_dryrun_action_intent_count": forbidden_dryrun_action_intent_count,
                "manager_dryrun_active": manager_dryrun_active,
                "body_dryrun_active": body_dryrun_active,
                "actions_requested": actions_requested,
                "allowed_action_intent_count": allowed_action_intent_count,
                "forbidden_action_intent_count": forbidden_action_intent_count,
                "executed_action_count": executed_action_count,
                "inputs_sent": inputs_sent,
                "input_action_counters": {
                    "actions_requested": actions_requested,
                    "inputs_sent": inputs_sent,
                },
                "no_input_sent": no_input_sent,
                "stop_reason": stop_reason,
                "forbidden_runtime_markers_absent": forbidden_runtime_markers_absent,
                "hidden_state_fields_absent": hidden_state_fields_absent,
                "planner_active": planner_active,
                "manager_active": manager_active,
                "body_active": body_active,
                "bridge_active": bridge_active,
                "learning_active": learning_active,
                "artifact_paths": {
                    "preflight_report": str(reports_dir / "preflight_report.json"),
                    "live_audit_pipeline": str(reports_dir / "live_audit_pipeline.json"),
                    "live_smoke_report": str(reports_dir / "live_smoke_report.json"),
                    "live_smoke_report_validation": str(
                        reports_dir / "live_smoke_report_validation.json"
                    ),
                    "review_summary": str(path),
                },
                "conclusion": conclusion,
                "recommended_next_step": "next",
                "failure_reasons": [] if conclusion == "passed" else ["synthetic_failure"],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def test_stability_review_passes_for_three_passing_runs(tmp_path: Path) -> None:
    paths = tuple(write_review(tmp_path, f"run_13_0b_observation_{index}") for index in range(3))

    summary = create_controlled_live_smoke_stability_review(
        review_paths=paths,
        created_at=FIXED_CREATED_AT,
    )

    assert summary.conclusion == "passed"
    assert summary.run_count == 3
    assert [run.run_id for run in summary.runs] == [
        "run_13_0b_observation_0",
        "run_13_0b_observation_1",
        "run_13_0b_observation_2",
    ]
    assert all(run.passed for run in summary.runs)


def test_stability_review_passes_for_three_disabled_observation_only_runs(tmp_path: Path) -> None:
    paths = tuple(
        write_review(
            tmp_path,
            f"run_13_0b_observation_{index}",
            action_logging_mode="disabled",
            actions_requested=0,
            inputs_sent=0,
            no_input_sent=True,
        )
        for index in range(3)
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=paths)

    assert summary.conclusion == "passed"
    assert all(run.action_logging_mode == "disabled" for run in summary.runs)
    assert all(run.passed for run in summary.runs)


def test_stability_review_passes_for_three_wait_only_noop_runs(tmp_path: Path) -> None:
    paths = tuple(
        write_review(
            tmp_path,
            f"run_13_1b_wait_only_noop_{index}",
            action_logging_mode="wait_only_noop",
            actions_requested=15,
            allowed_action_intent_count=15,
            forbidden_action_intent_count=0,
            executed_action_count=0,
            inputs_sent=0,
            no_input_sent=True,
        )
        for index in range(3)
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=paths)

    assert summary.conclusion == "passed"
    assert all(run.action_logging_mode == "wait_only_noop" for run in summary.runs)
    assert all(run.passed for run in summary.runs)


def test_stability_review_passes_for_three_dryrun_wait_only_runs(tmp_path: Path) -> None:
    paths = tuple(
        write_review(
            tmp_path,
            f"run_13_2_dryrun_wait_only_{index}",
            dryrun_orchestration_mode="wait_only",
            dryrun_task_count=30,
            dryrun_skill_count=30,
            allowed_dryrun_task_count=30,
            forbidden_dryrun_task_count=0,
            allowed_dryrun_action_intent_count=30,
            forbidden_dryrun_action_intent_count=0,
            manager_dryrun_active=True,
            body_dryrun_active=True,
            actions_requested=30,
            executed_action_count=0,
            inputs_sent=0,
            no_input_sent=True,
        )
        for index in range(3)
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=paths)

    assert summary.conclusion == "passed"
    assert all(run.dryrun_orchestration_mode == "wait_only" for run in summary.runs)
    assert all(run.passed for run in summary.runs)


def test_stability_review_fails_when_dryrun_wait_only_sent_inputs(tmp_path: Path) -> None:
    path = write_review(
        tmp_path,
        "run_13_2_dryrun_wait_only_inputs_sent",
        dryrun_orchestration_mode="wait_only",
        dryrun_task_count=30,
        dryrun_skill_count=30,
        allowed_dryrun_task_count=30,
        allowed_dryrun_action_intent_count=30,
        manager_dryrun_active=True,
        body_dryrun_active=True,
        actions_requested=30,
        inputs_sent=1,
        no_input_sent=False,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "inputs_sent_zero" in summary.runs[0].failure_reasons
    assert "dryrun_inputs_sent_zero" in summary.runs[0].failure_reasons
    assert "dryrun_no_input_sent_true" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_dryrun_wait_only_executed_action(
    tmp_path: Path,
) -> None:
    path = write_review(
        tmp_path,
        "run_13_2_dryrun_wait_only_executed",
        dryrun_orchestration_mode="wait_only",
        dryrun_task_count=30,
        dryrun_skill_count=30,
        allowed_dryrun_task_count=30,
        allowed_dryrun_action_intent_count=30,
        manager_dryrun_active=True,
        body_dryrun_active=True,
        actions_requested=30,
        executed_action_count=1,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "dryrun_executed_actions_zero" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_dryrun_wait_only_has_forbidden_task(
    tmp_path: Path,
) -> None:
    path = write_review(
        tmp_path,
        "run_13_2_dryrun_wait_only_forbidden_task",
        dryrun_orchestration_mode="wait_only",
        dryrun_task_count=30,
        dryrun_skill_count=30,
        allowed_dryrun_task_count=29,
        forbidden_dryrun_task_count=1,
        allowed_dryrun_action_intent_count=30,
        manager_dryrun_active=True,
        body_dryrun_active=True,
        actions_requested=30,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "dryrun_allowed_tasks_match" in summary.runs[0].failure_reasons
    assert "dryrun_forbidden_tasks_zero" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_dryrun_wait_only_manager_active(
    tmp_path: Path,
) -> None:
    path = write_review(
        tmp_path,
        "run_13_2_dryrun_wait_only_manager_active",
        dryrun_orchestration_mode="wait_only",
        dryrun_task_count=30,
        dryrun_skill_count=30,
        allowed_dryrun_task_count=30,
        allowed_dryrun_action_intent_count=30,
        manager_dryrun_active=True,
        body_dryrun_active=True,
        actions_requested=30,
        manager_active=True,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "manager_inactive" in summary.runs[0].failure_reasons
    assert "dryrun_manager_inactive" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_dryrun_wait_only_body_active(tmp_path: Path) -> None:
    path = write_review(
        tmp_path,
        "run_13_2_dryrun_wait_only_body_active",
        dryrun_orchestration_mode="wait_only",
        dryrun_task_count=30,
        dryrun_skill_count=30,
        allowed_dryrun_task_count=30,
        allowed_dryrun_action_intent_count=30,
        manager_dryrun_active=True,
        body_dryrun_active=True,
        actions_requested=30,
        body_active=True,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "body_inactive" in summary.runs[0].failure_reasons
    assert "dryrun_body_inactive" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_wait_only_noop_sent_inputs(tmp_path: Path) -> None:
    path = write_review(
        tmp_path,
        "run_13_1b_wait_only_noop_inputs_sent",
        action_logging_mode="wait_only_noop",
        actions_requested=15,
        allowed_action_intent_count=15,
        inputs_sent=1,
        no_input_sent=False,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "inputs_sent_zero" in summary.runs[0].failure_reasons
    assert "wait_only_noop_inputs_sent_zero" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_wait_only_noop_executed_action(
    tmp_path: Path,
) -> None:
    path = write_review(
        tmp_path,
        "run_13_1b_wait_only_noop_executed",
        action_logging_mode="wait_only_noop",
        actions_requested=15,
        allowed_action_intent_count=15,
        executed_action_count=1,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "wait_only_noop_executed_actions_zero" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_wait_only_noop_has_forbidden_action_intent(
    tmp_path: Path,
) -> None:
    path = write_review(
        tmp_path,
        "run_13_1b_wait_only_noop_forbidden",
        action_logging_mode="wait_only_noop",
        actions_requested=15,
        allowed_action_intent_count=14,
        forbidden_action_intent_count=1,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "wait_only_noop_allowed_action_intents_match" in summary.runs[0].failure_reasons
    assert "wait_only_noop_forbidden_action_intents_zero" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_disabled_mode_requested_actions(tmp_path: Path) -> None:
    path = write_review(
        tmp_path,
        "run_13_0b_observation_requested_actions",
        action_logging_mode="disabled",
        actions_requested=1,
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "disabled_actions_requested_zero" in summary.runs[0].failure_reasons


def test_stability_review_fails_for_unknown_action_logging_mode(tmp_path: Path) -> None:
    path = write_review(
        tmp_path,
        "run_unknown_action_logging_mode",
        action_logging_mode="unknown",
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))

    assert summary.conclusion == "failed"
    assert "action_logging_mode_disabled_or_wait_only_noop" in summary.runs[0].failure_reasons


def test_stability_review_fails_when_one_run_failed(tmp_path: Path) -> None:
    paths = (
        write_review(tmp_path, "run_0"),
        write_review(tmp_path, "run_1", conclusion="failed"),
        write_review(tmp_path, "run_2"),
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=paths)

    assert summary.conclusion == "failed"
    assert summary.runs[1].passed is False
    assert "conclusion_passed" in summary.runs[1].failure_reasons


def test_stability_review_fails_when_inputs_were_sent(tmp_path: Path) -> None:
    paths = (
        write_review(tmp_path, "run_0"),
        write_review(tmp_path, "run_1", inputs_sent=1),
        write_review(tmp_path, "run_2"),
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=paths)

    assert summary.conclusion == "failed"
    assert "inputs_sent_zero" in summary.runs[1].failure_reasons


def test_stability_review_fails_when_hidden_state_check_failed(tmp_path: Path) -> None:
    paths = (
        write_review(tmp_path, "run_0"),
        write_review(tmp_path, "run_1", hidden_state_fields_absent=False),
        write_review(tmp_path, "run_2"),
    )

    summary = create_controlled_live_smoke_stability_review(review_paths=paths)

    assert summary.conclusion == "failed"
    assert "hidden_state_fields_absent" in summary.runs[1].failure_reasons


def test_stability_review_missing_file_has_clear_error(tmp_path: Path) -> None:
    missing = tmp_path / "runs" / "missing" / "reports" / "controlled_live_smoke_review.json"

    with pytest.raises(ValueError, match="review file does not exist"):
        create_controlled_live_smoke_stability_review(review_paths=(missing,))


def test_stability_review_writer_refuses_to_overwrite(tmp_path: Path) -> None:
    path = write_review(tmp_path, "run_0")
    summary = create_controlled_live_smoke_stability_review(review_paths=(path,))
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
    assert "--review" in result.output
    assert "--output" in result.output


def test_cli_stability_review_writes_passing_summary(tmp_path: Path) -> None:
    paths = [write_review(tmp_path, f"run_{index}") for index in range(3)]
    output = tmp_path / "stability.json"
    args = ["controlled-live-smoke-stability-review", "--output", str(output)]
    for path in paths:
        args.extend(["--review", str(path)])

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "passed"
    assert payload["run_count"] == 3
