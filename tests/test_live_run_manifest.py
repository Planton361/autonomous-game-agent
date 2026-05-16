import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.evals.live_run_manifest as live_run_manifest_module
from fh_agent.cli import app
from fh_agent.evals.live_run_manifest import (
    ALLOWED_BRIDGE_FIELDS,
    FORBIDDEN_BRIDGE_FIELDS,
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


def manifest_for_test(
    tmp_path: Path,
    *,
    preflight: LiveRunPreflightResult | None = None,
    mode: str = "official_screen_only",
):
    return create_live_run_manifest(
        run_id="run_0001",
        mode=mode,  # type: ignore[arg-type]
        preflight_result=preflight or safe_preflight(tmp_path),
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        expected_window_title="Fear & Hunger",
        expected_resolution=FixedResolutionSnapshot(width=1280, height=720),
        created_at=FIXED_CREATED_AT,
        repo_metadata=FIXED_REPO_METADATA,
    )


def test_creates_manifest_from_passing_preflight(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)
    path = write_live_run_manifest(manifest)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert path == tmp_path / "runs" / "run_0001" / "reports" / "live_run_manifest.json"
    assert payload["run_id"] == "run_0001"
    assert payload["mode"] == "official_screen_only"
    assert payload["preflight_summary"]["ok"] is True
    assert payload["official_run_allowed"] is True
    assert payload["paths"]["events_jsonl"].endswith("runs/run_0001/events.jsonl")


def test_failed_preflight_sets_official_run_allowed_false(tmp_path: Path) -> None:
    failed_preflight = run_live_preflight(
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

    manifest = manifest_for_test(tmp_path, preflight=failed_preflight)

    assert manifest.preflight_summary.ok is False
    assert manifest.official_run_allowed is False
    assert manifest.preflight_summary.error_checks == ("no_spoiler_mode",)


def test_official_screen_only_manifest_disallows_debug_bridge(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)

    assert manifest.mode == "official_screen_only"
    assert manifest.official_run_allowed is True
    assert manifest.allowed_bridge_fields == ALLOWED_BRIDGE_FIELDS
    assert "map_id" not in manifest.allowed_bridge_fields
    assert "debug_oracle" not in manifest.model_dump_json()


def test_debug_visible_bridge_manifest_is_marked_non_official_or_debug(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path, mode="debug_visible_bridge")

    assert manifest.mode == "debug_visible_bridge"
    assert manifest.official_run_allowed is False


def test_manifest_contains_hidden_state_forbidden_field_snapshot(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)

    for field in (
        "map_id",
        "event_id",
        "event_name",
        "event_comments",
        "event_trigger_conditions",
        "game_switches",
        "game_variables",
        "enemy_database",
        "enemy_hp",
        "enemy_resistances",
        "item_database_effects",
        "ending_flags",
        "savegame_variables",
    ):
        assert field in manifest.forbidden_bridge_fields
        assert field in manifest.no_spoiler_policy.forbidden_hidden_state_fields
    assert manifest.forbidden_bridge_fields == FORBIDDEN_BRIDGE_FIELDS


def test_manifest_contains_conservative_safety_limits(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)

    assert manifest.safety_limits == LiveRunSafetyLimits()
    assert manifest.safety_limits.max_duration_seconds <= 60
    assert manifest.safety_limits.max_actions <= 50
    assert manifest.safety_limits.max_frames <= 180
    assert manifest.safety_limits.require_focused_window is True
    assert manifest.safety_limits.require_emergency_stop is True
    assert manifest.safety_limits.allow_real_input is False


def test_manifest_refuses_to_overwrite_existing_file_by_default(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)
    write_live_run_manifest(manifest)

    with pytest.raises(FileExistsError):
        write_live_run_manifest(manifest)


def test_manifest_can_overwrite_when_explicitly_requested(tmp_path: Path) -> None:
    manifest = manifest_for_test(tmp_path)
    path = write_live_run_manifest(manifest)
    path.write_text("old\n", encoding="utf-8")

    overwritten = write_live_run_manifest(manifest, overwrite=True)

    assert overwritten == path
    assert json.loads(path.read_text(encoding="utf-8"))["run_id"] == "run_0001"


def test_manifest_json_is_stable_and_serializable(tmp_path: Path) -> None:
    first = manifest_for_test(tmp_path)
    second = manifest_for_test(tmp_path)

    assert first.to_deterministic_json() == second.to_deterministic_json()
    payload = json.loads(first.to_deterministic_json())
    assert payload["created_at"] == "2026-05-16T12:00:00Z"
    assert payload["repo_metadata"] == {
        "branch": "main",
        "commit": "abc123",
        "dirty": False,
    }


def test_source_scan_blocks_live_runtime_imports() -> None:
    source = Path(live_run_manifest_module.__file__).read_text(encoding="utf-8")

    forbidden_import_terms = (
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.planner",
        "fh_agent.manager",
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


def test_cli_help_includes_live_manifest() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "live-manifest" in result.output


def test_cli_live_manifest_writes_manifest_from_preflight_report(tmp_path: Path) -> None:
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(safe_preflight(tmp_path).model_dump_json(), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "live-manifest",
            "--run-id",
            "run_0001",
            "--mode",
            "official_screen_only",
            "--preflight-report",
            str(preflight_path),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--screenshots-dir",
            str(tmp_path / "screenshots"),
        ],
    )

    assert result.exit_code == 0
    manifest_path = Path(result.output.strip())
    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["run_id"] == "run_0001"


def test_cli_live_manifest_fails_for_invalid_preflight_report(tmp_path: Path) -> None:
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text('{"not":"a preflight"}', encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "live-manifest",
            "--run-id",
            "run_0001",
            "--mode",
            "official_screen_only",
            "--preflight-report",
            str(preflight_path),
        ],
    )

    assert result.exit_code != 0
    assert "invalid preflight report" in result.output
