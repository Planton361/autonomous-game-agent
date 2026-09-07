import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.evals.live_audit_pipeline import run_live_audit_pipeline
from fh_agent.evals.live_run_manifest import (
    LEGACY_MANIFEST_STATUS,
    LegacyLiveRunManifest,
    LiveRunManifest,
    LiveRunSafetyLimits,
    RepoMetadata,
    create_live_run_manifest,
)
from fh_agent.evals.live_run_preflight import (
    LiveRunPreflightResult,
    PreflightCheckResult,
)
from fh_agent.evals.live_smoke_plan import create_live_smoke_plan, read_live_run_manifest

CANONICAL_MODES = (
    "screen-only",
    "bridge-assisted",
    "debug",
    "networked-api-exploratory",
    "contaminated",
)


def safe_preflight(run_id: str = "run-1") -> LiveRunPreflightResult:
    return LiveRunPreflightResult(
        ok=True,
        run_id=run_id,
        checks=(
            PreflightCheckResult(
                name="test",
                passed=True,
                message="test preflight passed",
                severity="info",
            ),
        ),
    )


def write_preflight(path: Path, run_id: str = "run-1") -> None:
    path.write_text(safe_preflight(run_id).model_dump_json() + "\n", encoding="utf-8")


def legacy_manifest_payload(tmp_path: Path, *, mode: str) -> dict[str, object]:
    run_id = "legacy-run"
    run_dir = tmp_path / "runs" / run_id
    reports_dir = run_dir / "reports"
    return {
        "manifest_version": "1",
        "run_id": run_id,
        "created_at": "2026-09-03T00:00:00Z",
        "mode": mode,
        "preflight_summary": {
            "ok": True,
            "run_id": run_id,
            "failed_checks": [],
            "error_checks": [],
        },
        "official_run_allowed": mode == "official_screen_only",
        "safety_limits": LiveRunSafetyLimits().model_dump(mode="json"),
        "allowed_bridge_fields": [
            "message_window_visible",
            "visible_message_text",
            "menu_open",
            "visible_menu_items",
            "combat_ui_visible",
            "death_screen_visible",
            "player_screen_position",
            "visible_sprite_screen_positions",
            "visible_sprite_visual_hashes",
            "screenshot_id",
        ],
        "forbidden_bridge_fields": [
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
        ],
        "paths": {
            "run_dir": str(run_dir),
            "events_jsonl": str(run_dir / "events.jsonl"),
            "screenshots_dir": str(tmp_path / "screenshots" / run_id),
            "reports_dir": str(reports_dir),
            "manifest_path": str(reports_dir / "live_run_manifest.json"),
        },
        "no_spoiler_policy": {
            "official_runs_must_not_use_hidden_state": True,
            "game_specific_claims_require_evidence_ids": True,
            "allowed_evidence_sources": [
                "screenshots",
                "visible_text",
                "sanitized_bridge_observations",
                "observed_outcomes",
            ],
            "forbidden_hidden_state_fields": [
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
            ],
        },
    }


@pytest.mark.parametrize("mode", CANONICAL_MODES)
def test_current_manifest_accepts_each_canonical_research_mode(
    tmp_path: Path,
    mode: str,
) -> None:
    manifest = create_live_run_manifest(
        run_id="run-1",
        mode=mode,  # type: ignore[arg-type]
        preflight_result=safe_preflight(),
        execution_mode="live",
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        repo_metadata=RepoMetadata(branch="test", commit="abc", dirty=False),
        created_at=datetime(2026, 9, 7, tzinfo=UTC),
    )

    assert manifest.manifest_version == "2"
    assert manifest.mode == mode
    assert manifest.execution_mode == "live"
    assert manifest.official_run_allowed is (mode in {"screen-only", "bridge-assisted"})


@pytest.mark.parametrize(
    "mode",
    ("official_screen_only", "debug_visible_bridge", "dry_run", "unknown"),
)
def test_current_manifest_rejects_legacy_and_unknown_research_modes(
    tmp_path: Path,
    mode: str,
) -> None:
    with pytest.raises(ValidationError):
        create_live_run_manifest(
            run_id="run-1",
            mode=mode,  # type: ignore[arg-type]
            preflight_result=safe_preflight(),
            runs_dir=tmp_path / "runs",
            screenshots_dir=tmp_path / "screenshots",
        )


def test_dry_run_is_a_separate_execution_mode_and_never_official(tmp_path: Path) -> None:
    manifest = create_live_run_manifest(
        run_id="run-1",
        mode="screen-only",
        execution_mode="dry-run",
        preflight_result=safe_preflight(),
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
    )

    assert manifest.mode == "screen-only"
    assert manifest.execution_mode == "dry-run"
    assert manifest.official_run_allowed is False
    payload = manifest.model_dump(mode="json")
    assert payload["mode"] != "dry_run"


@pytest.mark.parametrize(
    "legacy_mode",
    ("official_screen_only", "debug_visible_bridge", "dry_run"),
)
def test_legacy_v1_manifest_is_read_without_mode_reinterpretation(
    tmp_path: Path,
    legacy_mode: str,
) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(
        json.dumps(legacy_manifest_payload(tmp_path, mode=legacy_mode)) + "\n",
        encoding="utf-8",
    )

    artifact = read_live_run_manifest(path)

    assert isinstance(artifact, LegacyLiveRunManifest)
    assert artifact.legacy_status == LEGACY_MANIFEST_STATUS
    assert artifact.mode == legacy_mode

    with pytest.raises(ValueError, match="legacy v1 live-run manifests"):
        create_live_smoke_plan(manifest=artifact, source_manifest_path=path)


def test_bridge_assisted_flows_through_current_nonexecuting_audit_chain(tmp_path: Path) -> None:
    preflight_path = tmp_path / "preflight.json"
    write_preflight(preflight_path)

    result = run_live_audit_pipeline(
        run_id="run-1",
        preflight_report_path=preflight_path,
        mode="bridge-assisted",
        execution_mode="live",
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        repo_metadata=RepoMetadata(branch="test", commit="abc", dirty=False),
        created_at=datetime(2026, 9, 7, tzinfo=UTC),
    )

    assert result.mode == "bridge-assisted"
    assert result.execution_mode == "live"
    assert result.official_run_allowed is True
    manifest = LiveRunManifest.model_validate_json(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest.mode == "bridge-assisted"
    assert manifest.execution_mode == "live"
    plan = json.loads(result.smoke_plan_path.read_text(encoding="utf-8"))
    report = json.loads(result.smoke_report_path.read_text(encoding="utf-8"))
    assert plan["mode"] == report["mode"] == "bridge-assisted"
    assert plan["execution_mode"] == report["execution_mode"] == "live"


def test_dry_run_audit_chain_preserves_research_mode_but_blocks_official_execution(
    tmp_path: Path,
) -> None:
    preflight_path = tmp_path / "preflight.json"
    write_preflight(preflight_path)

    result = run_live_audit_pipeline(
        run_id="run-1",
        preflight_report_path=preflight_path,
        mode="screen-only",
        execution_mode="dry-run",
        runs_dir=tmp_path / "runs",
        screenshots_dir=tmp_path / "screenshots",
        created_at=datetime(2026, 9, 7, tzinfo=UTC),
    )

    assert result.mode == "screen-only"
    assert result.execution_mode == "dry-run"
    assert result.official_run_allowed is False
    assert "execution_mode_dry_run" in result.validation_errors
