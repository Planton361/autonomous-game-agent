import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.evals.live_smoke_report as live_smoke_report_module
from fh_agent.cli import app
from fh_agent.evals.live_run_manifest import (
    FixedResolutionSnapshot,
    RepoMetadata,
    create_live_run_manifest,
)
from fh_agent.evals.live_run_preflight import (
    FixedResolution,
    LiveRunPreflightConfig,
    LiveRunPreflightResult,
    run_live_preflight,
)
from fh_agent.evals.live_smoke_plan import (
    LiveSmokeRunPlan,
    create_live_smoke_plan,
    write_live_smoke_plan,
)
from fh_agent.evals.live_smoke_report import (
    LiveSmokeRunReport,
    create_noop_live_smoke_report,
    read_live_smoke_plan,
    write_live_smoke_report,
)

FIXED_CREATED_AT = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
FIXED_REPO_METADATA = RepoMetadata(branch="main", commit="abc123", dirty=False)


def safe_preflight(tmp_path: Path, *, run_id: str = "run_0001") -> LiveRunPreflightResult:
    return run_live_preflight(
        LiveRunPreflightConfig(
            runs_dir=tmp_path / "runs",
            evidence_dir=tmp_path / "screenshots",
            run_id=run_id,
            no_spoiler_mode=True,
            emergency_stop_required=True,
            focus_guard_required=True,
            fixed_resolution=FixedResolution(width=1280, height=720),
            live_inputs_enabled=False,
            bridge_hidden_state_enabled=False,
            debug_oracle_enabled=False,
        )
    )


def failed_preflight(tmp_path: Path) -> LiveRunPreflightResult:
    return run_live_preflight(
        LiveRunPreflightConfig(
            runs_dir=tmp_path / "runs",
            evidence_dir=tmp_path / "screenshots",
            run_id="run_0001",
            no_spoiler_mode=False,
            emergency_stop_required=True,
            focus_guard_required=True,
            fixed_resolution=FixedResolution(width=1280, height=720),
            live_inputs_enabled=False,
            bridge_hidden_state_enabled=False,
            debug_oracle_enabled=False,
        )
    )


def plan_for_test(
    tmp_path: Path,
    *,
    preflight: LiveRunPreflightResult | None = None,
) -> LiveSmokeRunPlan:
    manifest = create_live_run_manifest(
        run_id="run_0001",
        mode="official_screen_only",
        preflight_result=preflight or safe_preflight(tmp_path),
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        expected_window_title="Fear & Hunger",
        expected_resolution=FixedResolutionSnapshot(width=1280, height=720),
        created_at=FIXED_CREATED_AT,
        repo_metadata=FIXED_REPO_METADATA,
    )
    return create_live_smoke_plan(
        manifest=manifest,
        source_manifest_path=manifest.paths.manifest_path,
        source_preflight_path=tmp_path / "preflight.json",
        created_at=FIXED_CREATED_AT,
    )


def report_for_test(
    tmp_path: Path,
    *,
    preflight: LiveRunPreflightResult | None = None,
):
    plan = plan_for_test(tmp_path, preflight=preflight)
    return create_noop_live_smoke_report(
        plan=plan,
        source_plan_path=plan.expected_outputs.smoke_plan_path,
        created_at=FIXED_CREATED_AT,
    )


def readiness_gap_names(report: LiveSmokeRunReport) -> tuple[str, ...]:
    return tuple(gap.name for gap in report.readiness_gaps)


def test_creates_noop_report_from_valid_plan(tmp_path: Path) -> None:
    report = report_for_test(tmp_path)
    path = write_live_smoke_report(report)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert path == tmp_path / "runs" / "run_0001" / "reports" / "live_smoke_report.json"
    assert payload["report_version"] == "1"
    assert payload["run_id"] == "run_0001"
    assert payload["execution_status"] == "not_executed"
    assert payload["official_run_allowed"] is True


def test_report_execution_status_is_always_not_executed(tmp_path: Path) -> None:
    report = report_for_test(tmp_path)
    payload = report.model_dump(mode="json")

    assert report.execution_status == "not_executed"
    with pytest.raises(ValueError):
        LiveSmokeRunReport.model_validate({**payload, "execution_status": "executed"})


def test_report_execution_enabled_is_always_false(tmp_path: Path) -> None:
    report = report_for_test(tmp_path)
    payload = report.model_dump(mode="json")

    assert report.execution_enabled is False
    with pytest.raises(ValueError, match="must never enable execution"):
        LiveSmokeRunReport.model_validate({**payload, "execution_enabled": True})


def test_report_never_claims_runtime_observations_or_actions(tmp_path: Path) -> None:
    report = report_for_test(tmp_path)
    payload = report.model_dump(mode="json")

    assert payload["observed_outputs"] == {}
    runtime_claim_terms = (
        "screenshots_captured",
        "actions_sent",
        "observations_created",
        "frames_captured",
        "runtime_events",
    )
    for term in runtime_claim_terms:
        assert term not in payload["observed_outputs"]
    with pytest.raises(ValueError, match="must not claim observed runtime outputs"):
        LiveSmokeRunReport.model_validate({**payload, "observed_outputs": {"events_jsonl": None}})


def test_failed_plan_forces_official_run_allowed_false(tmp_path: Path) -> None:
    report = report_for_test(tmp_path, preflight=failed_preflight(tmp_path))

    assert report.official_run_allowed is False
    assert "official_run_not_allowed" in readiness_gap_names(report)


def test_report_contains_readiness_gap_for_disabled_execution(tmp_path: Path) -> None:
    report = report_for_test(tmp_path)
    gap = report.readiness_gaps[0]

    assert gap.name == "execution_disabled"
    assert gap.severity == "info"


def test_report_includes_plan_validation_errors_as_readiness_gaps(tmp_path: Path) -> None:
    report = report_for_test(tmp_path, preflight=failed_preflight(tmp_path))

    names = readiness_gap_names(report)
    assert "preflight_not_allowed" in names
    assert "manifest_not_allowed" in names
    assert "preflight_not_allowed" in report.blocked_reasons
    assert "manifest_not_allowed" in report.blocked_reasons


def test_report_copies_stop_conditions(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)
    report = create_noop_live_smoke_report(
        plan=plan,
        source_plan_path=plan.expected_outputs.smoke_plan_path,
        created_at=FIXED_CREATED_AT,
    )

    assert report.stop_conditions == plan.stop_conditions


def test_report_copies_expected_outputs(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)
    report = create_noop_live_smoke_report(
        plan=plan,
        source_plan_path=plan.expected_outputs.smoke_plan_path,
        created_at=FIXED_CREATED_AT,
    )

    assert report.expected_outputs == plan.expected_outputs


def test_report_copies_no_spoiler_policy_snapshot(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)
    report = create_noop_live_smoke_report(
        plan=plan,
        source_plan_path=plan.expected_outputs.smoke_plan_path,
        created_at=FIXED_CREATED_AT,
    )

    assert report.no_spoiler_policy_snapshot == plan.no_spoiler_policy_snapshot
    assert "map_id" in report.no_spoiler_policy_snapshot.forbidden_hidden_state_fields
    assert "enemy_hp" in report.no_spoiler_policy_snapshot.forbidden_hidden_state_fields


def test_report_refuses_to_overwrite_existing_file_by_default(tmp_path: Path) -> None:
    report = report_for_test(tmp_path)
    write_live_smoke_report(report)

    with pytest.raises(FileExistsError):
        write_live_smoke_report(report)


def test_report_can_overwrite_when_explicitly_requested(tmp_path: Path) -> None:
    report = report_for_test(tmp_path)
    path = write_live_smoke_report(report)
    path.write_text("old\n", encoding="utf-8")

    overwritten = write_live_smoke_report(report, overwrite=True)

    assert overwritten == path
    assert json.loads(path.read_text(encoding="utf-8"))["execution_status"] == "not_executed"


def test_report_json_is_stable_and_serializable(tmp_path: Path) -> None:
    first = report_for_test(tmp_path)
    second = report_for_test(tmp_path)

    assert first.to_deterministic_json() == second.to_deterministic_json()
    payload = json.loads(first.to_deterministic_json())
    assert payload["created_at"] == "2026-05-16T12:00:00Z"
    assert payload["execution_enabled"] is False
    assert payload["observed_outputs"] == {}


def test_cli_help_includes_live_smoke_report() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "live-smoke-report" in result.output


def test_cli_live_smoke_report_writes_report_from_plan(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)
    plan_path = write_live_smoke_plan(plan)

    result = CliRunner().invoke(
        app,
        [
            "live-smoke-report",
            "--plan",
            str(plan_path),
        ],
    )

    assert result.exit_code == 0
    report_path = Path(result.output.strip())
    assert report_path.is_file()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["execution_status"] == "not_executed"
    assert payload["observed_outputs"] == {}


def test_cli_live_smoke_report_fails_for_invalid_plan(tmp_path: Path) -> None:
    plan_path = tmp_path / "invalid_plan.json"
    plan_path.write_text('{"run_id":"run_0001"}', encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "live-smoke-report",
            "--plan",
            str(plan_path),
        ],
    )

    assert result.exit_code != 0
    assert "invalid live-smoke plan" in result.output


def test_read_live_smoke_plan_rejects_invalid_plan(tmp_path: Path) -> None:
    plan_path = tmp_path / "invalid_plan.json"
    plan_path.write_text('{"run_id":"run_0001"}', encoding="utf-8")

    with pytest.raises(ValueError, match="invalid live-smoke plan"):
        read_live_smoke_plan(plan_path)


def test_source_scan_blocks_live_runtime_imports() -> None:
    source = Path(live_smoke_report_module.__file__).read_text(encoding="utf-8")

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
