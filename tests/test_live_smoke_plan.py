import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.evals.live_smoke_plan as live_smoke_plan_module
from fh_agent.cli import app
from fh_agent.evals.live_run_manifest import (
    FixedResolutionSnapshot,
    LiveRunSafetyLimits,
    RepoMetadata,
    create_live_run_manifest,
    write_live_run_manifest,
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
    read_live_run_manifest,
    write_live_smoke_plan,
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


def manifest_for_test(
    tmp_path: Path,
    *,
    preflight: LiveRunPreflightResult | None = None,
    safety_limits: LiveRunSafetyLimits | None = None,
):
    return create_live_run_manifest(
        run_id="run_0001",
        mode="official_screen_only",
        preflight_result=preflight or safe_preflight(tmp_path),
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        safety_limits=safety_limits,
        expected_window_title="Fear & Hunger",
        expected_resolution=FixedResolutionSnapshot(width=1280, height=720),
        created_at=FIXED_CREATED_AT,
        repo_metadata=FIXED_REPO_METADATA,
    )


def plan_for_test(
    tmp_path: Path,
    *,
    preflight: LiveRunPreflightResult | None = None,
    safety_limits: LiveRunSafetyLimits | None = None,
) -> LiveSmokeRunPlan:
    manifest = manifest_for_test(
        tmp_path,
        preflight=preflight,
        safety_limits=safety_limits,
    )
    return create_live_smoke_plan(
        manifest=manifest,
        source_manifest_path=manifest.paths.manifest_path,
        source_preflight_path=tmp_path / "preflight.json",
        created_at=FIXED_CREATED_AT,
    )


def stop_condition_by_name(plan: LiveSmokeRunPlan, name: str):
    matches = [condition for condition in plan.stop_conditions if condition.name == name]
    assert len(matches) == 1
    return matches[0]


def test_creates_plan_from_valid_manifest(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)
    plan = create_live_smoke_plan(
        manifest=manifest,
        source_manifest_path=manifest.paths.manifest_path,
        created_at=FIXED_CREATED_AT,
    )
    path = write_live_smoke_plan(plan)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert path == tmp_path / "runs" / "run_0001" / "reports" / "live_smoke_plan.json"
    assert payload["run_id"] == "run_0001"
    assert payload["plan_version"] == "1"
    assert payload["mode"] == "official_screen_only"
    assert payload["official_run_allowed"] is True


def test_plan_execution_is_always_disabled(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)
    payload = plan.model_dump(mode="json")

    assert plan.execution_enabled is False
    assert payload["execution_enabled"] is False
    with pytest.raises(ValueError, match="must never enable execution"):
        LiveSmokeRunPlan.model_validate({**payload, "execution_enabled": True})


def test_failed_manifest_forces_official_run_allowed_false(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path, preflight=failed_preflight(tmp_path))

    assert plan.official_run_allowed is False
    assert "preflight_not_allowed" in plan.validation_errors
    assert "manifest_not_allowed" in plan.validation_errors


def test_plan_contains_required_stop_conditions(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)

    assert tuple(condition.name for condition in plan.stop_conditions) == (
        "max_duration",
        "max_actions",
        "max_frames",
        "focus_lost",
        "emergency_stop",
        "hidden_state_violation",
        "preflight_not_allowed",
        "manifest_not_allowed",
        "runtime_error",
    )


def test_stop_condition_thresholds_match_manifest_safety_limits(tmp_path: Path) -> None:
    limits = LiveRunSafetyLimits(max_duration_seconds=45, max_actions=12, max_frames=90)
    plan = plan_for_test(tmp_path, safety_limits=limits)

    assert stop_condition_by_name(plan, "max_duration").threshold == 45
    assert stop_condition_by_name(plan, "max_actions").threshold == 12
    assert stop_condition_by_name(plan, "max_frames").threshold == 90
    assert stop_condition_by_name(plan, "focus_lost").threshold is True
    assert stop_condition_by_name(plan, "emergency_stop").threshold is True


def test_plan_contains_expected_output_paths(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)

    assert plan.expected_outputs.events_jsonl == tmp_path / "runs" / "run_0001" / "events.jsonl"
    assert plan.expected_outputs.screenshots_dir == tmp_path / "screenshots" / "run_0001"
    assert plan.expected_outputs.reports_dir == tmp_path / "runs" / "run_0001" / "reports"
    assert (
        plan.expected_outputs.final_report_path
        == tmp_path / "runs" / "run_0001" / "reports" / "live_smoke_report.json"
    )
    assert (
        plan.expected_outputs.smoke_plan_path
        == tmp_path / "runs" / "run_0001" / "reports" / "live_smoke_plan.json"
    )


def test_plan_copies_no_spoiler_policy_snapshot(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)
    plan = create_live_smoke_plan(
        manifest=manifest,
        source_manifest_path=manifest.paths.manifest_path,
        created_at=FIXED_CREATED_AT,
    )

    assert plan.no_spoiler_policy_snapshot == manifest.no_spoiler_policy
    assert "map_id" in plan.no_spoiler_policy_snapshot.forbidden_hidden_state_fields
    assert "enemy_hp" in plan.no_spoiler_policy_snapshot.forbidden_hidden_state_fields


def test_invalid_manifest_missing_required_fields_is_rejected_or_marked_invalid(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "invalid_manifest.json"
    manifest_path.write_text('{"run_id":"run_0001"}', encoding="utf-8")

    with pytest.raises(ValueError, match="invalid live-run manifest"):
        read_live_run_manifest(manifest_path)


def test_plan_refuses_to_overwrite_existing_file_by_default(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)
    write_live_smoke_plan(plan)

    with pytest.raises(FileExistsError):
        write_live_smoke_plan(plan)


def test_plan_can_overwrite_when_explicitly_requested(tmp_path: Path) -> None:
    plan = plan_for_test(tmp_path)
    path = write_live_smoke_plan(plan)
    path.write_text("old\n", encoding="utf-8")

    overwritten = write_live_smoke_plan(plan, overwrite=True)

    assert overwritten == path
    assert json.loads(path.read_text(encoding="utf-8"))["run_id"] == "run_0001"


def test_plan_json_is_stable_and_serializable(tmp_path: Path) -> None:
    first = plan_for_test(tmp_path)
    second = plan_for_test(tmp_path)

    assert first.to_deterministic_json() == second.to_deterministic_json()
    payload = json.loads(first.to_deterministic_json())
    assert payload["created_at"] == "2026-05-16T12:00:00Z"
    assert payload["execution_enabled"] is False


def test_cli_help_includes_live_smoke_plan() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "live-smoke-plan" in result.output


def test_cli_live_smoke_plan_writes_plan_from_manifest(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)
    manifest_path = write_live_run_manifest(manifest)

    result = CliRunner().invoke(
        app,
        [
            "live-smoke-plan",
            "--manifest",
            str(manifest_path),
        ],
    )

    assert result.exit_code == 0
    plan_path = Path(result.output.strip())
    assert plan_path.is_file()
    assert json.loads(plan_path.read_text(encoding="utf-8"))["execution_enabled"] is False


def test_cli_live_smoke_plan_fails_for_invalid_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "invalid_manifest.json"
    manifest_path.write_text('{"run_id":"run_0001"}', encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "live-smoke-plan",
            "--manifest",
            str(manifest_path),
        ],
    )

    assert result.exit_code != 0
    assert "invalid live-run manifest" in result.output


def test_source_scan_blocks_live_runtime_imports() -> None:
    source = Path(live_smoke_plan_module.__file__).read_text(encoding="utf-8")

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
