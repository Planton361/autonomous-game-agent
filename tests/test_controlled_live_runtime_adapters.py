import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

import fh_agent.evals.controlled_live_runtime_adapters as adapters_module
from fh_agent.evals.controlled_live_runtime_adapters import (
    CaptureCommandError,
    FocusCheckAdapter,
    OneFrameCaptureAdapter,
    StopFileEmergencyStopAdapter,
    SubprocessPpmCaptureBackend,
    build_controlled_runtime_adapters,
)
from fh_agent.evals.controlled_live_smoke_runner import run_controlled_live_smoke
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


class FakeCaptureBackend:
    def __init__(self, *, stop_file_to_create: Path | None = None) -> None:
        self.count = 0
        self.stop_file_to_create = stop_file_to_create

    def capture(self):
        from fh_agent.perception.screen_capture import ScreenFrame

        if self.stop_file_to_create is not None and self.count == 0:
            self.stop_file_to_create.write_text("stop\n", encoding="utf-8")
        value = self.count % 256
        self.count += 1
        return ScreenFrame(
            width=1,
            height=1,
            rgb=bytes([value, value, value]),
            captured_at=FIXED_CREATED_AT,
        )


@dataclass(frozen=True, slots=True)
class FakeEvidenceRecord:
    evidence_id: str
    path: str
    created_at: datetime
    width: int
    height: int
    sha256: str


class DeterministicEvidenceStore:
    def __init__(self, root: Path, *, run_id: str) -> None:
        self.index = 0
        self.root = root
        self.run_id = run_id

    def next_id(self) -> str:
        value = f"evidence-{self.index}"
        self.index += 1
        return value

    def save_screenshot(self, frame):
        evidence_id = self.next_id()
        run_dir = self.root / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{evidence_id}.ppm"
        path.write_bytes(frame.to_ppm_bytes())
        return FakeEvidenceRecord(
            evidence_id=evidence_id,
            path=str(path),
            created_at=frame.captured_at,
            width=frame.width,
            height=frame.height,
            sha256=sha256(path.read_bytes()).hexdigest(),
        )


def write_pipeline_summary(
    tmp_path: Path,
    *,
    safety_limits: LiveRunSafetyLimits | None = None,
) -> Path:
    preflight = run_live_preflight(
        LiveRunPreflightConfig(
            runs_dir=tmp_path / "runs",
            evidence_dir=tmp_path / "screenshots",
            run_id="run_0001",
            no_spoiler_mode=True,
            emergency_stop_required=True,
            focus_guard_required=True,
            fixed_resolution=FixedResolution(width=1280, height=720),
            live_inputs_enabled=False,
            bridge_hidden_state_enabled=False,
            debug_oracle_enabled=False,
        )
    )
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(preflight.model_dump_json(), encoding="utf-8")
    result = run_live_audit_pipeline(
        run_id="run_0001",
        preflight_report_path=preflight_path,
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


def test_real_runtime_factory_refuses_without_allow_real_runtime(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="allow_real_runtime=True"):
        build_controlled_runtime_adapters(
            allow_real_runtime=False,
            run_id="run_0001",
            target_window_title="Fear & Hunger",
            capture_backend=FakeCaptureBackend(),
        )


def test_real_runtime_factory_allows_real_input_flag_without_sender(tmp_path: Path) -> None:
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        allow_real_input=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
    )

    assert bundle.focus_check() is True


def test_stop_file_emergency_adapter_reports_available_and_not_triggered(tmp_path: Path) -> None:
    adapter = StopFileEmergencyStopAdapter(tmp_path / "run" / "STOP")

    assert adapter.is_available() is True
    assert adapter.is_triggered() is False


def test_stop_file_emergency_adapter_reports_triggered_when_file_exists(tmp_path: Path) -> None:
    stop_file = tmp_path / "run" / "STOP"
    stop_file.parent.mkdir(parents=True)
    stop_file.write_text("stop\n", encoding="utf-8")
    adapter = StopFileEmergencyStopAdapter(stop_file)

    assert adapter.is_available() is True
    assert adapter.is_triggered() is True


def test_focus_adapter_reports_unfocused_from_fake_window_probe() -> None:
    adapter = FocusCheckAdapter(
        target_title="Fear & Hunger",
        window_title_probe=lambda: "Other Window",
    )

    assert adapter() is False


def test_concrete_capture_backend_is_lazy_loaded(tmp_path: Path) -> None:
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_command="definitely-missing-capture-command",
    )

    assert bundle.focus_check() is True


def test_concrete_capture_backend_writes_screenshot_from_fake_backend(tmp_path: Path) -> None:
    backend = SubprocessPpmCaptureBackend(
        (sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'P6\\n1 1\\n255\\nabc')"),
        clock=lambda: FIXED_CREATED_AT,
    )
    adapter = OneFrameCaptureAdapter(
        capture_backend=backend,
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    frame = adapter()

    assert frame.screenshot_path is not None
    assert frame.screenshot_path.read_bytes() == b"P6\n1 1\n255\nabc"


def test_subprocess_capture_backend_accepts_synthetic_ppm_p6() -> None:
    backend = SubprocessPpmCaptureBackend(
        (sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'P6\\n2 1\\n255\\nabcdef')"),
        clock=lambda: FIXED_CREATED_AT,
    )

    frame = backend.capture()

    assert frame.width == 2
    assert frame.height == 1
    assert frame.to_ppm_bytes() == b"P6\n2 1\n255\nabcdef"


def test_subprocess_capture_error_contains_diagnostics_without_image_data() -> None:
    backend = SubprocessPpmCaptureBackend(
        (
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('bad capture\\n'); "
            "sys.stdout.buffer.write(b'P6\\n10240 2880\\n255\\nabc'); sys.exit(7)",
        ),
        clock=lambda: FIXED_CREATED_AT,
    )

    with pytest.raises(CaptureCommandError) as exc_info:
        backend.capture()

    diagnostic = exc_info.value.diagnostic
    assert diagnostic.command[0] == sys.executable
    assert diagnostic.return_code == 7
    assert diagnostic.stderr_excerpt == "bad capture\n"
    assert diagnostic.stdout_byte_count == len(b"P6\n10240 2880\n255\nabc")
    assert diagnostic.ppm_header is not None
    assert diagnostic.ppm_header.valid is True
    assert diagnostic.ppm_header.width == 10240
    assert set(diagnostic.model_dump()) == {
        "command",
        "return_code",
        "stderr_excerpt",
        "stdout_byte_count",
        "ppm_header",
        "exception_message",
    }


def test_concrete_capture_backend_returns_evidence_metadata(tmp_path: Path) -> None:
    backend = SubprocessPpmCaptureBackend(
        (
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'P6\\n2 1\\n255\\nabcdef')",
        ),
        clock=lambda: FIXED_CREATED_AT,
    )
    adapter = OneFrameCaptureAdapter(
        capture_backend=backend,
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    frame = adapter()

    assert frame.evidence_id == "evidence-0"
    assert frame.timestamp == FIXED_CREATED_AT
    assert frame.width == 2
    assert frame.height == 1
    assert frame.sha256


def test_capture_adapter_records_one_screenshot_from_fake_capture_backend(tmp_path: Path) -> None:
    adapter = OneFrameCaptureAdapter(
        capture_backend=FakeCaptureBackend(),
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    frame = adapter()

    assert frame.evidence_id == "evidence-0"
    assert frame.screenshot_path is not None
    assert frame.screenshot_path.is_file()
    assert frame.timestamp == FIXED_CREATED_AT
    assert frame.width == 1
    assert frame.height == 1
    assert frame.sha256 is not None


def test_capture_adapter_writes_screenshot_under_run_specific_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
    )

    frame = bundle.capture_frame()

    assert frame.screenshot_path is not None
    assert frame.screenshot_path.parent == Path("runs/run_0001/screenshots")
    assert frame.screenshot_path.is_file()


def test_runner_with_real_adapter_factory_captures_one_frame_observation_only(
    tmp_path: Path,
) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=1, max_actions=0),
    )
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )
    logged = []

    result = run_controlled_live_smoke(
        user_started=True,
        pipeline_summary_path=summary_path,
        focus_check=bundle.focus_check,
        emergency_stop_available=bundle.emergency_stop_available,
        emergency_stop_triggered=bundle.emergency_stop_triggered,
        capture_frame=bundle.capture_frame,
        log_event=logged.append,
        now=lambda: FIXED_CREATED_AT,
        report_path=tmp_path / "controlled_report.json",
        overwrite=True,
    )

    assert result.status.frames_captured == 1
    assert result.status.actions_requested == 0
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["runtime_mode"] == "observation_only"
    assert report["captured_frame_count"] == 1


def test_report_uses_run_specific_screenshot_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=1, max_actions=0),
    )
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
    )

    result = run_controlled_live_smoke(
        user_started=True,
        pipeline_summary_path=summary_path,
        focus_check=bundle.focus_check,
        emergency_stop_available=bundle.emergency_stop_available,
        emergency_stop_triggered=bundle.emergency_stop_triggered,
        capture_frame=bundle.capture_frame,
        log_event=lambda event: None,
        now=lambda: FIXED_CREATED_AT,
        report_path=tmp_path / "controlled_report.json",
        overwrite=True,
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    screenshot_path = Path(payload["screenshot_paths"][0])

    assert payload["screenshot_evidence"][0]["screenshot_path"] == str(screenshot_path)
    assert screenshot_path.parent == Path("runs/run_0001/screenshots")


def test_multi_frame_screenshots_are_run_specific(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=3, max_actions=0),
    )
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
    )

    result = run_controlled_live_smoke(
        user_started=True,
        pipeline_summary_path=summary_path,
        focus_check=bundle.focus_check,
        emergency_stop_available=bundle.emergency_stop_available,
        emergency_stop_triggered=bundle.emergency_stop_triggered,
        capture_frame=bundle.capture_frame,
        log_event=lambda event: None,
        now=lambda: FIXED_CREATED_AT,
        report_path=tmp_path / "controlled_report.json",
        max_frames=3,
        overwrite=True,
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    screenshot_paths = [Path(value) for value in payload["screenshot_paths"]]

    assert len(screenshot_paths) == 3
    assert all(path.parent == Path("runs/run_0001/screenshots") for path in screenshot_paths)
    assert all(path.is_file() for path in screenshot_paths)


def test_no_global_live_audit_pipeline_screenshot_dir_is_used(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
    )

    frame = bundle.capture_frame()

    assert frame.screenshot_path is not None
    assert "screenshots/live_audit_pipeline" not in frame.screenshot_path.as_posix()
    assert not Path("screenshots/live_audit_pipeline").exists()


def test_runner_refuses_when_target_window_not_focused(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(tmp_path)
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: False,
        capture_backend=FakeCaptureBackend(),
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    with pytest.raises(ValueError, match="focus check failed"):
        run_controlled_live_smoke(
            user_started=True,
            pipeline_summary_path=summary_path,
            focus_check=bundle.focus_check,
            emergency_stop_available=bundle.emergency_stop_available,
            emergency_stop_triggered=bundle.emergency_stop_triggered,
            capture_frame=bundle.capture_frame,
            log_event=lambda event: None,
        )


def test_runner_refuses_when_stop_file_already_triggered(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(tmp_path)
    stop_file = tmp_path / "STOP"
    stop_file.write_text("stop\n", encoding="utf-8")
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        stop_file_path=stop_file,
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    with pytest.raises(ValueError, match="already triggered"):
        run_controlled_live_smoke(
            user_started=True,
            pipeline_summary_path=summary_path,
            focus_check=bundle.focus_check,
            emergency_stop_available=bundle.emergency_stop_available,
            emergency_stop_triggered=bundle.emergency_stop_triggered,
            capture_frame=bundle.capture_frame,
            log_event=lambda event: None,
        )


def test_runner_stops_when_stop_file_appears_mid_run(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=3, max_actions=0),
    )
    stop_file = tmp_path / "STOP"
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        stop_file_path=stop_file,
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(stop_file_to_create=stop_file),
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    result = run_controlled_live_smoke(
        user_started=True,
        pipeline_summary_path=summary_path,
        focus_check=bundle.focus_check,
        emergency_stop_available=bundle.emergency_stop_available,
        emergency_stop_triggered=bundle.emergency_stop_triggered,
        capture_frame=bundle.capture_frame,
        log_event=lambda event: None,
        now=lambda: FIXED_CREATED_AT,
        report_path=tmp_path / "controlled_report.json",
        overwrite=True,
    )

    assert result.status.stop_reason == "emergency_stop_triggered"
    assert result.status.frames_captured == 1


def test_report_contains_screenshot_evidence_metadata(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=1, max_actions=0),
    )
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    result = run_controlled_live_smoke(
        user_started=True,
        pipeline_summary_path=summary_path,
        focus_check=bundle.focus_check,
        emergency_stop_available=bundle.emergency_stop_available,
        emergency_stop_triggered=bundle.emergency_stop_triggered,
        capture_frame=bundle.capture_frame,
        log_event=lambda event: None,
        now=lambda: FIXED_CREATED_AT,
        report_path=tmp_path / "controlled_report.json",
        overwrite=True,
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert payload["evidence_ids"] == ["evidence-0"]
    assert payload["screenshot_paths"][0].endswith("evidence-0.ppm")
    assert payload["screenshot_evidence"][0]["screenshot_path"].endswith("evidence-0.ppm")
    assert payload["screenshot_evidence"][0]["sha256"]


def test_report_contains_no_input_sent_flag(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=1, max_actions=0),
    )
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    result = run_controlled_live_smoke(
        user_started=True,
        pipeline_summary_path=summary_path,
        focus_check=bundle.focus_check,
        emergency_stop_available=bundle.emergency_stop_available,
        emergency_stop_triggered=bundle.emergency_stop_triggered,
        capture_frame=bundle.capture_frame,
        log_event=lambda event: None,
        now=lambda: FIXED_CREATED_AT,
        report_path=tmp_path / "controlled_report.json",
        overwrite=True,
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert payload["no_input_sent"] is True


def test_controlled_live_smoke_still_records_no_input_sent_true(tmp_path: Path) -> None:
    summary_path = write_pipeline_summary(
        tmp_path,
        safety_limits=LiveRunSafetyLimits(max_frames=1, max_actions=0),
    )
    bundle = build_controlled_runtime_adapters(
        allow_real_runtime=True,
        run_id="run_0001",
        target_window_title="Fear & Hunger",
        focused_probe=lambda: True,
        capture_backend=FakeCaptureBackend(),
        evidence_store=DeterministicEvidenceStore(tmp_path / "screenshots", run_id="run_0001"),
    )

    result = run_controlled_live_smoke(
        user_started=True,
        pipeline_summary_path=summary_path,
        focus_check=bundle.focus_check,
        emergency_stop_available=bundle.emergency_stop_available,
        emergency_stop_triggered=bundle.emergency_stop_triggered,
        capture_frame=bundle.capture_frame,
        log_event=lambda event: None,
        now=lambda: FIXED_CREATED_AT,
        report_path=tmp_path / "controlled_report.json",
        overwrite=True,
    )
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert payload["no_input_sent"] is True


def test_source_scan_blocks_planner_manager_body_rl_training_torch_sb3_bridge_runtime() -> None:
    source = Path(adapters_module.__file__).read_text(encoding="utf-8")

    forbidden_terms = (
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
        "keyboard",
        "xdotool key",
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
