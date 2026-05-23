import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.evals.controlled_live_smoke_runner as runner_module
from fh_agent.cli import app
from fh_agent.evals.controlled_live_smoke_runner import (
    CaptureErrorDiagnostic,
    ControlledLiveSmokeEvent,
    ControlledLiveSmokeFrame,
    ControlledLiveSmokeReport,
    ControlledLiveSmokeResult,
    PpmHeaderParseDiagnostic,
    run_controlled_live_smoke,
)
from fh_agent.evals.live_audit_pipeline import (
    run_live_audit_pipeline,
    write_live_audit_pipeline_result,
)
from fh_agent.evals.live_run_manifest import (
    FixedResolutionSnapshot,
    LiveRunSafetyLimits,
    RepoMetadata,
)
from fh_agent.evals.live_run_preflight import (
    FixedResolution,
    LiveRunPreflightConfig,
    run_live_preflight,
)

FIXED_CREATED_AT = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
FIXED_REPO_METADATA = RepoMetadata(branch="main", commit="abc123", dirty=False)


class SequenceBool:
    def __init__(self, values: list[bool]) -> None:
        self.values = values
        self.index = 0

    def __call__(self) -> bool:
        if self.index >= len(self.values):
            return self.values[-1]
        value = self.values[self.index]
        self.index += 1
        return value


class FakeCapture:
    def __init__(
        self,
        *,
        fail_after: int | None = None,
        screenshot_root: Path | None = None,
    ) -> None:
        self.count = 0
        self.fail_after = fail_after
        self.screenshot_root = screenshot_root

    def __call__(self) -> ControlledLiveSmokeFrame:
        if self.fail_after is not None and self.count >= self.fail_after:
            raise RuntimeError("capture failed")
        evidence_id = f"evidence-{self.count}"
        screenshot_path = (
            self.screenshot_root / f"{evidence_id}.ppm"
            if self.screenshot_root is not None
            else None
        )
        frame = ControlledLiveSmokeFrame(
            evidence_id=evidence_id,
            screenshot_path=screenshot_path,
        )
        self.count += 1
        return frame


class DiagnosticCaptureFailure:
    def __call__(self) -> ControlledLiveSmokeFrame:
        diagnostic = CaptureErrorDiagnostic(
            command=("capture", "--active-window"),
            return_code=2,
            stderr_excerpt="capture failed\n",
            stdout_byte_count=12,
            ppm_header=PpmHeaderParseDiagnostic(
                present=True,
                valid=False,
                error="invalid PPM header from capture command",
            ),
            exception_message="capture command failed",
        )
        error = RuntimeError("capture command failed")
        error.diagnostic = diagnostic  # type: ignore[attr-defined]
        raise error


class FakeClock:
    def __init__(self, values: list[float]) -> None:
        self.values = values
        self.index = 0

    def __call__(self) -> float:
        if self.index >= len(self.values):
            return self.values[-1]
        value = self.values[self.index]
        self.index += 1
        return value


def write_preflight_report(tmp_path: Path, *, no_spoiler_mode: bool = True) -> Path:
    result = run_live_preflight(
        LiveRunPreflightConfig(
            runs_dir=tmp_path / "runs",
            evidence_dir=tmp_path / "screenshots",
            run_id="run_0001",
            no_spoiler_mode=no_spoiler_mode,
            emergency_stop_required=True,
            focus_guard_required=True,
            fixed_resolution=FixedResolution(width=1280, height=720),
            live_inputs_enabled=False,
            bridge_hidden_state_enabled=False,
            debug_oracle_enabled=False,
        )
    )
    path = tmp_path / "preflight.json"
    path.write_text(result.model_dump_json(), encoding="utf-8")
    return path


def write_pipeline_summary(
    tmp_path: Path,
    *,
    no_spoiler_mode: bool = True,
    safety_limits: LiveRunSafetyLimits | None = None,
) -> Path:
    preflight_report = write_preflight_report(tmp_path, no_spoiler_mode=no_spoiler_mode)
    result = run_live_audit_pipeline(
        run_id="run_0001",
        preflight_report_path=preflight_report,
        mode="official_screen_only",
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        expected_resolution=FixedResolutionSnapshot(width=1280, height=720),
        overwrite=True,
        created_at=FIXED_CREATED_AT,
        repo_metadata=FIXED_REPO_METADATA,
    )
    if safety_limits is not None:
        payload = json.loads(result.smoke_plan_path.read_text(encoding="utf-8"))
        payload["safety_limits"] = safety_limits.model_dump(mode="json")
        result.smoke_plan_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return write_live_audit_pipeline_result(result, overwrite=True)


def event_log() -> tuple[
    list[ControlledLiveSmokeEvent], Callable[[ControlledLiveSmokeEvent], None]
]:
    events: list[ControlledLiveSmokeEvent] = []

    def log(event: ControlledLiveSmokeEvent) -> None:
        events.append(event)

    return events, log


def run_with_fakes(
    tmp_path: Path,
    *,
    summary_path: Path | None = None,
    focus_values: list[bool] | None = None,
    emergency_available: bool = True,
    emergency_values: list[bool] | None = None,
    capture: FakeCapture | None = None,
    clock: FakeClock | None = None,
    user_started: bool = True,
    max_frames: int | None = None,
    output_run_dir: Path | None = None,
    action_logging_mode: str = "disabled",
    dryrun_orchestration_mode: str = "disabled",
    noop_action_frequency: int = 1,
) -> tuple[ControlledLiveSmokeResult, list[ControlledLiveSmokeEvent]]:
    logged, logger = event_log()
    result = run_controlled_live_smoke(
        user_started=user_started,
        pipeline_summary_path=summary_path or write_pipeline_summary(tmp_path),
        focus_check=SequenceBool(focus_values or [True]),
        emergency_stop_available=lambda: emergency_available,
        emergency_stop_triggered=SequenceBool(emergency_values or [False]),
        capture_frame=capture or FakeCapture(),
        log_event=logger,
        clock=clock or FakeClock([0, 0, 0, 0, 0, 0, 0]),
        now=lambda: FIXED_CREATED_AT,
        report_path=None if output_run_dir is not None else tmp_path / "controlled_report.json",
        output_run_dir=output_run_dir,
        max_frames=max_frames,
        action_logging_mode=action_logging_mode,  # type: ignore[arg-type]
        dryrun_orchestration_mode=dryrun_orchestration_mode,  # type: ignore[arg-type]
        noop_action_frequency=noop_action_frequency,
        overwrite=True,
    )
    return result, logged


def test_runner_refuses_without_user_started_flag(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="user_started=True"):
        run_with_fakes(tmp_path, user_started=False)


def test_runner_refuses_when_pipeline_blocks_official_run(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(tmp_path, no_spoiler_mode=False)

    with pytest.raises(ValueError, match="does not allow"):
        run_with_fakes(tmp_path, summary_path=summary_path)


def test_runner_refuses_when_focus_check_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="focus check failed"):
        run_with_fakes(tmp_path, focus_values=[False])


def test_runner_refuses_when_emergency_stop_unavailable(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unavailable"):
        run_with_fakes(tmp_path, emergency_available=False)


def test_runner_refuses_when_emergency_stop_already_triggered(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="already triggered"):
        run_with_fakes(tmp_path, emergency_values=[True])


def test_runner_enforces_max_frames(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=2, max_actions=0),
    )

    result, _ = run_with_fakes(tmp_path, summary_path=summary_path)

    assert result.status.stop_reason == "max_frames_reached"
    assert result.status.frames_captured == 2


def test_multi_frame_runner_captures_three_frames_with_fake_adapter(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=3, max_actions=0),
    )

    result, logged = run_with_fakes(tmp_path, summary_path=summary_path, max_frames=3)

    assert result.status.stop_reason == "max_frames_reached"
    assert result.status.frames_captured == 3
    assert [event.event_type for event in logged].count("frame_captured") == 3


def test_multi_frame_report_contains_three_evidence_ids_and_paths(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=3, max_actions=0),
    )
    screenshot_root = Path("runs/run_0001/screenshots")

    result, _ = run_with_fakes(
        tmp_path,
        summary_path=summary_path,
        capture=FakeCapture(screenshot_root=screenshot_root),
        max_frames=3,
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert payload["evidence_ids"] == ["evidence-0", "evidence-1", "evidence-2"]
    assert payload["screenshot_paths"] == [
        "runs/run_0001/screenshots/evidence-0.ppm",
        "runs/run_0001/screenshots/evidence-1.ppm",
        "runs/run_0001/screenshots/evidence-2.ppm",
    ]


def test_max_frames_above_thirty_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="between 1 and 30"):
        run_with_fakes(tmp_path, max_frames=31)


def test_runner_enforces_max_duration(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_duration_seconds=1, max_frames=10),
    )

    result, _ = run_with_fakes(
        tmp_path,
        summary_path=summary_path,
        clock=FakeClock([0, 2]),
    )

    assert result.status.stop_reason == "max_duration_reached"
    assert result.status.frames_captured == 0


def test_runner_enforces_zero_or_wait_only_action_budget(tmp_path: Path) -> None:
    result, logged = run_with_fakes(tmp_path)

    assert result.status.actions_requested == 0
    assert "noop_action_intent" not in [event.event_type for event in logged]
    assert "wait_intent" not in [event.event_type for event in logged]


def test_runner_logs_wait_only_noop_action_intents_without_inputs(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=3, max_actions=0),
    )

    result, logged = run_with_fakes(
        tmp_path,
        summary_path=summary_path,
        max_frames=3,
        action_logging_mode="wait_only_noop",
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert result.status.actions_requested == 3
    assert payload["action_logging_mode"] == "wait_only_noop"
    assert payload["inputs_sent"] == 0
    assert payload["no_input_sent"] is True
    assert len(payload["requested_actions"]) == 3
    assert payload["executed_actions"] == []
    assert all(action["action"] == "wait" for action in payload["requested_actions"])
    assert all(action["executed"] is False for action in payload["requested_actions"])
    assert all(action["input_sent"] is False for action in payload["requested_actions"])
    assert [event.event_type for event in logged].count("wait_intent") == 3


def test_wait_only_noop_frequency_controls_intent_count(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=3, max_actions=0),
    )

    result, _ = run_with_fakes(
        tmp_path,
        summary_path=summary_path,
        max_frames=3,
        action_logging_mode="wait_only_noop",
        noop_action_frequency=2,
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert result.status.actions_requested == 1
    assert len(payload["requested_actions"]) == 1
    assert payload["requested_actions"][0]["frame_index"] == 1


def test_runner_logs_dryrun_wait_only_task_path_without_inputs(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=3, max_actions=0),
    )

    result, logged = run_with_fakes(
        tmp_path,
        summary_path=summary_path,
        max_frames=3,
        dryrun_orchestration_mode="wait_only",
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert result.status.actions_requested == 3
    assert payload["action_logging_mode"] == "disabled"
    assert payload["dryrun_orchestration_mode"] == "wait_only"
    assert payload["manager_dryrun_active"] is True
    assert payload["body_dryrun_active"] is True
    assert payload["manager_orchestration_active"] is False
    assert payload["body_control_active"] is False
    assert payload["inputs_sent"] == 0
    assert payload["no_input_sent"] is True
    assert payload["dryrun_task_count"] == 3
    assert payload["dryrun_skill_count"] == 3
    assert len(payload["dryrun_tasks"]) == 3
    assert len(payload["requested_actions"]) == 3
    assert payload["executed_actions"] == []
    assert {task["static_goal"] for task in payload["dryrun_tasks"]} == {
        "maintain_observation_without_input"
    }
    assert {task["selected_skill"] for task in payload["dryrun_tasks"]} == {"wait"}
    assert all(task["action_intent"]["action"] == "wait" for task in payload["dryrun_tasks"])
    assert all(task["action_intent"]["executed"] is False for task in payload["dryrun_tasks"])
    assert all(task["action_intent"]["input_sent"] is False for task in payload["dryrun_tasks"])
    assert [event.event_type for event in logged].count("dryrun_task_intent") == 3


def test_runner_rejects_combined_dryrun_and_wait_only_noop(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        run_with_fakes(
            tmp_path,
            action_logging_mode="wait_only_noop",
            dryrun_orchestration_mode="wait_only",
        )


def test_runner_rejects_invalid_noop_action_frequency(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="noop_action_frequency"):
        run_with_fakes(
            tmp_path,
            action_logging_mode="wait_only_noop",
            noop_action_frequency=0,
        )


def test_runner_logs_runtime_start_and_end_events(tmp_path: Path) -> None:
    _, logged = run_with_fakes(tmp_path)

    assert logged[0].event_type == "runtime_start"
    assert logged[-1].event_type == "runtime_end"


def test_runner_logs_frame_events_with_evidence_ids_from_fake_capture(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=2, max_actions=0),
    )

    _, logged = run_with_fakes(tmp_path, summary_path=summary_path)

    frame_events = [event for event in logged if event.event_type == "frame_captured"]
    assert [event.evidence_id for event in frame_events] == ["evidence-0", "evidence-1"]


def test_runner_stops_when_focus_is_lost_mid_run(tmp_path: Path) -> None:
    result, _ = run_with_fakes(tmp_path, focus_values=[True, True, False])

    assert result.status.stop_reason == "focus_lost"
    assert result.status.frames_captured == 1


def test_focus_lost_between_frames_stops_before_max_frames(tmp_path: Path) -> None:
    result, _ = run_with_fakes(
        tmp_path,
        focus_values=[True, True, False],
        max_frames=3,
    )

    assert result.status.stop_reason == "focus_lost"
    assert result.status.frames_captured < 3


def test_runner_stops_when_emergency_stop_triggers_mid_run(tmp_path: Path) -> None:
    result, _ = run_with_fakes(tmp_path, emergency_values=[False, False, True])

    assert result.status.stop_reason == "emergency_stop_triggered"
    assert result.status.frames_captured == 1


def test_stop_file_between_frames_stops_before_max_frames(tmp_path: Path) -> None:
    result, _ = run_with_fakes(
        tmp_path,
        emergency_values=[False, False, True],
        max_frames=3,
    )

    assert result.status.stop_reason == "emergency_stop_triggered"
    assert result.status.frames_captured < 3


def test_runner_writes_final_controlled_smoke_report(tmp_path: Path) -> None:
    result, _ = run_with_fakes(tmp_path)

    assert result.report_path.is_file()
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["report_version"] == "1"
    assert payload["run_id"] == "run_0001"


def test_capture_error_report_contains_diagnostics(tmp_path: Path) -> None:
    result, _ = run_with_fakes(tmp_path, capture=DiagnosticCaptureFailure())  # type: ignore[arg-type]
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert payload["status"]["stop_reason"] == "capture_error"
    diagnostic = payload["capture_error_diagnostic"]
    assert diagnostic["command"] == ["capture", "--active-window"]
    assert diagnostic["return_code"] == 2
    assert diagnostic["stderr_excerpt"] == "capture failed\n"
    assert diagnostic["stdout_byte_count"] == 12
    assert diagnostic["ppm_header"]["present"] is True
    assert diagnostic["ppm_header"]["valid"] is False
    assert diagnostic["exception_message"] == "capture command failed"


def test_output_run_dir_writes_new_report_without_overwriting_old_run_dir(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(tmp_path)
    old_report = tmp_path / "runs" / "run_0001" / "reports" / "live_smoke_report.json"
    old_before = old_report.read_text(encoding="utf-8")
    output_run_dir = tmp_path / "runs" / "run_13_0a_observation_30"

    result, _ = run_with_fakes(
        tmp_path,
        summary_path=summary_path,
        output_run_dir=output_run_dir,
    )

    assert result.run_id == "run_13_0a_observation_30"
    assert result.report_path == output_run_dir / "reports" / "live_smoke_report.json"
    assert result.report_path.is_file()
    assert old_report.read_text(encoding="utf-8") == old_before


def test_report_does_not_claim_autonomous_planner_or_body_control(tmp_path: Path) -> None:
    result, _ = run_with_fakes(tmp_path)
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert payload["autonomous_planner_active"] is False
    assert payload["manager_orchestration_active"] is False
    assert payload["body_control_active"] is False
    assert payload["learning_active"] is False
    with pytest.raises(ValueError, match="must not claim autonomous control"):
        ControlledLiveSmokeReport.model_validate({**payload, "autonomous_planner_active": True})


def test_cli_help_includes_controlled_live_smoke() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "controlled-live-smoke" in result.output


def test_cli_help_includes_real_runtime_flags() -> None:
    result = CliRunner().invoke(app, ["controlled-live-smoke", "--help"])

    assert result.exit_code == 0
    assert "--allow-real-runtime" in result.output
    assert "--allow-real-input" in result.output
    assert "--target-window-title" in result.output
    assert "--stop-file" in result.output
    assert "--run-dir" in result.output
    assert "--action-logging-mode" in result.output
    assert "dryrun-orchestrati" in result.output
    assert "noop-action" in result.output
    assert "observation-only" in result.output


def test_cli_controlled_live_smoke_refuses_without_user_started(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "controlled-live-smoke",
            "--pipeline-summary",
            str(tmp_path / "summary.json"),
        ],
    )

    assert result.exit_code != 0
    assert "requires --user-started" in result.output


def test_cli_real_runtime_requires_user_started(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "controlled-live-smoke",
            "--pipeline-summary",
            str(tmp_path / "summary.json"),
            "--allow-real-runtime",
            "--target-window-title",
            "Fear & Hunger",
            "--capture-command",
            "fake-capture",
        ],
    )

    assert result.exit_code != 0
    assert "requires --user-started" in result.output


def test_cli_real_runtime_rejects_allow_real_input_true(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "controlled-live-smoke",
            "--pipeline-summary",
            str(tmp_path / "summary.json"),
            "--user-started",
            "--allow-real-runtime",
            "--allow-real-input",
            "--target-window-title",
            "Fear & Hunger",
            "--capture-command",
            "fake-capture",
        ],
    )

    assert result.exit_code != 0
    assert "no real input adapter" in result.output


def test_allow_real_input_true_still_rejected(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "controlled-live-smoke",
            "--pipeline-summary",
            str(tmp_path / "summary.json"),
            "--user-started",
            "--allow-real-runtime",
            "--allow-real-input",
            "--target-window-title",
            "Fear & Hunger",
            "--capture-command",
            "fake-capture",
        ],
    )

    assert result.exit_code != 0
    assert "no real input adapter" in result.output


def test_cli_real_runtime_defaults_to_max_frames_one() -> None:
    result = CliRunner().invoke(app, ["controlled-live-smoke", "--help"])

    assert result.exit_code == 0
    assert "--max-frames" in result.output
    assert "[1<=x<=30]" in result.output
    assert "[default: 1]" in result.output


def test_max_frames_default_remains_one() -> None:
    result = CliRunner().invoke(app, ["controlled-live-smoke", "--help"])

    assert result.exit_code == 0
    assert "[default: 1]" in result.output


def test_source_scan_blocks_planner_manager_body_rl_training_torch_sb3_hidden_imports() -> None:
    source = Path(runner_module.__file__).read_text(encoding="utf-8")

    forbidden_terms = (
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.planner",
        "llm_client",
        "fh_agent.manager",
        "task_manager",
        "orchestrator",
        "fh_agent.body",
        "fh_agent.rl",
        "InputExecutor",
        "input_executor",
        "torch",
        "stable_baselines3",
        "pyautogui",
        "mss",
        "PaddleOCR",
        "paddleocr",
        "map_id",
        "event_id",
        "event_name",
        "game_switches",
        "game_variables",
    )
    for term in forbidden_terms:
        assert term not in source
