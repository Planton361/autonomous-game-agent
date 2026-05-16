import json
from pathlib import Path

from typer.testing import CliRunner

import fh_agent.evals.live_run_preflight as live_run_preflight_module
from fh_agent.cli import app
from fh_agent.evals.live_run_preflight import (
    FixedResolution,
    LiveRunPreflightConfig,
    LiveRunPreflightResult,
    run_live_preflight,
)


def safe_config(tmp_path: Path, *, run_id: str = "smoke") -> LiveRunPreflightConfig:
    return LiveRunPreflightConfig(
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


def check_by_name(result: LiveRunPreflightResult, name: str):
    matches = [check for check in result.checks if check.name == name]
    assert len(matches) == 1
    return matches[0]


def test_successful_preflight_with_safe_test_configuration(tmp_path: Path) -> None:
    result = run_live_preflight(safe_config(tmp_path))

    assert result.ok is True
    assert result.run_id == "smoke"
    assert all(check.passed for check in result.checks)
    assert (tmp_path / "runs" / "smoke").is_dir()
    assert (tmp_path / "screenshots" / "smoke").is_dir()
    assert not (tmp_path / "runs" / "smoke" / ".preflight_write_probe").exists()


def test_missing_run_id_can_be_generated_deterministically(tmp_path: Path) -> None:
    config = safe_config(tmp_path, run_id="")

    result = run_live_preflight(config, run_id_factory=lambda: "generated-run")

    assert result.ok is True
    assert result.run_id == "generated-run"
    assert check_by_name(result, "run_id").passed is True


def test_missing_no_spoiler_mode_is_error_and_not_ok(tmp_path: Path) -> None:
    result = run_live_preflight(safe_config(tmp_path).model_copy(update={"no_spoiler_mode": False}))

    check = check_by_name(result, "no_spoiler_mode")
    assert result.ok is False
    assert check.passed is False
    assert check.severity == "error"


def test_live_inputs_enabled_is_error_but_does_not_execute(tmp_path: Path) -> None:
    result = run_live_preflight(
        safe_config(tmp_path).model_copy(update={"live_inputs_enabled": True})
    )

    check = check_by_name(result, "live_inputs_enabled")
    assert result.ok is False
    assert check.passed is False
    assert check.severity == "error"
    assert "disabled" not in check.message


def test_missing_fixed_resolution_is_error(tmp_path: Path) -> None:
    result = run_live_preflight(safe_config(tmp_path).model_copy(update={"fixed_resolution": None}))

    check = check_by_name(result, "fixed_resolution")
    assert result.ok is False
    assert check.passed is False
    assert check.severity == "error"


def test_incomplete_fixed_resolution_is_error(tmp_path: Path) -> None:
    result = run_live_preflight(
        safe_config(tmp_path).model_copy(update={"fixed_resolution": FixedResolution(width=1280)})
    )

    check = check_by_name(result, "fixed_resolution")
    assert result.ok is False
    assert check.passed is False
    assert "width and height" in check.message


def test_non_writable_run_path_is_detected_portably(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "runs"
    blocked_parent.write_text("not a directory", encoding="utf-8")

    result = run_live_preflight(
        safe_config(tmp_path).model_copy(update={"runs_dir": blocked_parent})
    )

    check = check_by_name(result, "run_directory_writable")
    assert result.ok is False
    assert check.passed is False
    assert check.severity == "error"


def test_non_writable_evidence_path_is_detected_portably(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "screenshots"
    blocked_parent.write_text("not a directory", encoding="utf-8")

    result = run_live_preflight(
        safe_config(tmp_path).model_copy(update={"evidence_dir": blocked_parent})
    )

    check = check_by_name(result, "evidence_directory_writable")
    assert result.ok is False
    assert check.passed is False
    assert check.severity == "error"


def test_hidden_state_or_debug_oracle_flag_is_error(tmp_path: Path) -> None:
    result = run_live_preflight(
        safe_config(tmp_path).model_copy(
            update={"bridge_hidden_state_enabled": True, "debug_oracle_enabled": True}
        )
    )

    check = check_by_name(result, "hidden_state_sources_disabled")
    assert result.ok is False
    assert check.passed is False
    assert check.severity == "error"
    assert "bridge_hidden_state" in check.message
    assert "debug_oracle" in check.message


def test_result_is_deterministic_and_json_serializable(tmp_path: Path) -> None:
    result_a = run_live_preflight(safe_config(tmp_path))
    result_b = run_live_preflight(safe_config(tmp_path))

    assert result_a.model_dump(mode="json") == result_b.model_dump(mode="json")
    assert json.loads(result_a.model_dump_json())["ok"] is True
    assert json.loads(result_a.to_deterministic_json()) == result_a.model_dump(mode="json")


def test_preflight_module_has_no_live_runtime_imports() -> None:
    source = Path(live_run_preflight_module.__file__).read_text(encoding="utf-8")

    forbidden_import_terms = (
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.planner",
        "fh_agent.manager",
        "fh_agent.body",
        "fh_agent.rl",
        "InputExecutor",
        "ScreenCapture",
        "pyautogui",
        "mss",
    )
    for term in forbidden_import_terms:
        assert term not in source


def test_cli_live_preflight_reports_json_without_live_actions(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "live-preflight",
            "--run-id",
            "smoke",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--evidence-dir",
            str(tmp_path / "screenshots"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["run_id"] == "smoke"
