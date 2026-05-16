import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.evals.live_audit_pipeline as live_audit_pipeline_module
from fh_agent.cli import app
from fh_agent.evals.live_audit_pipeline import (
    LiveAuditPipelineResult,
    run_live_audit_pipeline,
    write_live_audit_pipeline_result,
)
from fh_agent.evals.live_run_manifest import RepoMetadata
from fh_agent.evals.live_run_preflight import (
    FixedResolution,
    LiveRunPreflightConfig,
    LiveRunPreflightResult,
    run_live_preflight,
)

FIXED_CREATED_AT = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
FIXED_REPO_METADATA = RepoMetadata(branch="main", commit="abc123", dirty=False)


def preflight_result(tmp_path: Path, *, no_spoiler_mode: bool = True) -> LiveRunPreflightResult:
    return run_live_preflight(
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


def write_preflight_report(
    tmp_path: Path,
    *,
    no_spoiler_mode: bool = True,
) -> Path:
    path = tmp_path / "preflight.json"
    path.write_text(
        preflight_result(tmp_path, no_spoiler_mode=no_spoiler_mode).model_dump_json(),
        encoding="utf-8",
    )
    return path


def run_pipeline(
    tmp_path: Path,
    *,
    no_spoiler_mode: bool = True,
    overwrite: bool = False,
) -> LiveAuditPipelineResult:
    return run_live_audit_pipeline(
        run_id="run_0001",
        preflight_report_path=write_preflight_report(
            tmp_path,
            no_spoiler_mode=no_spoiler_mode,
        ),
        mode="official_screen_only",
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        overwrite=overwrite,
        created_at=FIXED_CREATED_AT,
        repo_metadata=FIXED_REPO_METADATA,
    )


def stage_statuses(result: LiveAuditPipelineResult) -> dict[str, str]:
    return {stage.name: stage.status for stage in result.stages}


def test_pipeline_creates_manifest_plan_report_and_summary(tmp_path: Path) -> None:
    result = run_pipeline(tmp_path)
    summary_path = write_live_audit_pipeline_result(result)

    assert result.official_run_allowed is True
    assert result.manifest_path.is_file()
    assert result.smoke_plan_path.is_file()
    assert result.smoke_report_path.is_file()
    assert summary_path.is_file()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "run_0001"
    assert payload["official_run_allowed"] is True


def test_pipeline_execution_is_always_disabled(tmp_path: Path) -> None:
    result = run_pipeline(tmp_path)
    payload = result.model_dump(mode="json")

    assert result.execution_enabled is False
    with pytest.raises(ValueError, match="must never enable execution"):
        LiveAuditPipelineResult.model_validate({**payload, "execution_enabled": True})


def test_failed_preflight_propagates_official_run_allowed_false(tmp_path: Path) -> None:
    result = run_pipeline(tmp_path, no_spoiler_mode=False)
    write_live_audit_pipeline_result(result)

    assert result.official_run_allowed is False
    assert "preflight_not_allowed" in result.validation_errors
    assert "manifest_not_allowed" in result.validation_errors
    assert "official_run_not_allowed" in result.validation_errors


def test_pipeline_refuses_to_overwrite_existing_artifacts_by_default(tmp_path: Path) -> None:
    first = run_pipeline(tmp_path)
    write_live_audit_pipeline_result(first)

    second = run_pipeline(tmp_path)

    assert stage_statuses(second)["manifest"] == "failed"
    assert "manifest already exists" in second.validation_errors[0]
    with pytest.raises(FileExistsError):
        write_live_audit_pipeline_result(second)


def test_pipeline_can_overwrite_when_explicitly_requested(tmp_path: Path) -> None:
    first = run_pipeline(tmp_path)
    write_live_audit_pipeline_result(first)

    second = run_pipeline(tmp_path, overwrite=True)
    summary_path = write_live_audit_pipeline_result(second, overwrite=True)

    assert second.official_run_allowed is True
    assert all(stage.status == "succeeded" for stage in second.stages)
    assert json.loads(summary_path.read_text(encoding="utf-8"))["execution_enabled"] is False


def test_pipeline_records_stage_statuses(tmp_path: Path) -> None:
    result = run_pipeline(tmp_path)

    assert stage_statuses(result) == {
        "preflight": "succeeded",
        "manifest": "succeeded",
        "smoke_plan": "succeeded",
        "smoke_report": "succeeded",
    }


def test_pipeline_records_partial_failure_without_fabricating_later_success(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "runs" / "run_0001" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "live_smoke_plan.json").write_text("already here\n", encoding="utf-8")

    result = run_live_audit_pipeline(
        run_id="run_0001",
        preflight_report_path=write_preflight_report(tmp_path),
        mode="official_screen_only",
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        created_at=FIXED_CREATED_AT,
        repo_metadata=FIXED_REPO_METADATA,
    )

    statuses = stage_statuses(result)
    assert statuses["preflight"] == "succeeded"
    assert statuses["manifest"] == "succeeded"
    assert statuses["smoke_plan"] == "failed"
    assert statuses["smoke_report"] == "skipped"
    assert result.official_run_allowed is False


def test_pipeline_summary_json_is_stable_and_serializable(tmp_path: Path) -> None:
    first = run_pipeline(tmp_path)
    second = run_pipeline(tmp_path / "other")

    first_payload = json.loads(first.to_deterministic_json())
    assert first_payload["created_at"] == "2026-05-16T12:00:00Z"
    assert first_payload["execution_enabled"] is False
    assert first.to_deterministic_json() == first.to_deterministic_json()
    assert second.to_deterministic_json() == second.to_deterministic_json()


def test_pipeline_uses_existing_artifact_functions_without_runtime_imports() -> None:
    source = Path(live_audit_pipeline_module.__file__).read_text(encoding="utf-8")

    required_function_names = (
        "read_preflight_report",
        "create_live_run_manifest",
        "write_live_run_manifest",
        "read_live_run_manifest",
        "create_live_smoke_plan",
        "write_live_smoke_plan",
        "read_live_smoke_plan",
        "create_noop_live_smoke_report",
        "write_live_smoke_report",
    )
    for name in required_function_names:
        assert name in source
    assert "LiveRunManifest.model_validate" not in source
    assert "LiveSmokeRunPlan.model_validate" not in source


def test_cli_help_includes_live_audit_pipeline() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "live-audit-pipeline" in result.output


def test_cli_live_audit_pipeline_writes_summary_path(tmp_path: Path) -> None:
    preflight_report = write_preflight_report(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "live-audit-pipeline",
            "--run-id",
            "run_0001",
            "--preflight-report",
            str(preflight_report),
            "--mode",
            "official_screen_only",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--screenshots-dir",
            str(tmp_path / "screenshots"),
        ],
    )

    assert result.exit_code == 0
    summary_path = Path(result.output.strip())
    assert summary_path.is_file()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["execution_enabled"] is False


def test_cli_live_audit_pipeline_fails_for_invalid_preflight_report(tmp_path: Path) -> None:
    preflight_report = tmp_path / "invalid_preflight.json"
    preflight_report.write_text('{"run_id":"run_0001"}', encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "live-audit-pipeline",
            "--run-id",
            "run_0001",
            "--preflight-report",
            str(preflight_report),
            "--mode",
            "official_screen_only",
            "--runs-dir",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code != 0
    assert "live audit pipeline failed" in result.output
    summary_path = tmp_path / "runs" / "run_0001" / "reports" / "live_audit_pipeline.json"
    assert summary_path.is_file()


def test_source_scan_blocks_live_runtime_imports() -> None:
    source = Path(live_audit_pipeline_module.__file__).read_text(encoding="utf-8")

    forbidden_import_terms = (
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
        "ScreenCapture",
        "bridge_server",
        "torch",
        "stable_baselines3",
        "pyautogui",
        "mss",
        "PaddleOCR",
        "paddleocr",
    )
    for term in forbidden_import_terms:
        assert term not in source
