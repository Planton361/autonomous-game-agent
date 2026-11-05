import copy
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

import fh_agent.pilot_step as pilot_step_module
from fh_agent.cli import app
from fh_agent.game import xdotool_adapters
from fh_agent.game.input_executor import DryRunInputBackend
from fh_agent.pilot_step import (
    PilotStepLimits,
    PilotStepScenarioError,
    build_pilot_step_report,
    load_pilot_step_scenario,
    run_pilot_step,
    semantic_report,
)

SCENARIO_PATH = (
    Path(__file__).resolve().parents[1] / "configs/replay/pilot_step_visible_object_v1.json"
)


def base_scenario() -> dict[str, Any]:
    return json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))


def field_frame(evidence_id: str, visual_hash: str = "dhash:0123456789abcdef") -> dict[str, Any]:
    return {
        "screenshot_evidence_id": evidence_id,
        "payload": {
            "run_mode": "bridge-assisted",
            "ui_state": "field",
            "visible_sprite_screen_positions": [[120, 80]],
            "visible_sprite_visual_hashes": [visual_hash],
            "screenshot_id": evidence_id,
        },
    }


def write_scenario(tmp_path: Path, scenario: dict[str, Any]) -> Path:
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(scenario), encoding="utf-8")
    return path


def run_report(
    tmp_path: Path,
    scenario: dict[str, Any],
    *,
    limits: PilotStepLimits | None = None,
    stop: bool = False,
    run_name: str = "run",
) -> tuple[dict[str, Any], pilot_step_module.PilotStepRun]:
    loaded, digest = load_pilot_step_scenario(write_scenario(tmp_path, scenario))
    stop_file = tmp_path / f"{run_name}-STOP"
    if stop:
        stop_file.write_text("stop", encoding="utf-8")
    run = run_pilot_step(
        loaded,
        scenario_sha256=digest,
        run_dir=tmp_path / run_name,
        stop_file=stop_file,
        limits=limits,
    )
    return build_pilot_step_report(run), run


def assert_non_official(report: dict[str, Any]) -> None:
    assert report["result_classification"] == "debug-replay"
    assert report["official_evidence"] is False
    assert report["live_gameplay_verified"] is False
    assert report["causal_gameplay_success"] is False
    assert report["input_backend"] == "DryRunInputBackend"


def test_cli_replays_one_interaction_through_verifier_closure(tmp_path: Path) -> None:
    report_path = tmp_path / "out" / "report.json"

    result = CliRunner().invoke(
        app,
        ["pilot-step", "--scenario", str(SCENARIO_PATH), "--report", str(report_path)],
    )

    assert result.exit_code == 0, result.output
    assert "debug-replay outcome=replay_local_verifier_success" in result.output
    assert "live_gameplay_verified=false" in result.output
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert_non_official(report)
    assert report["outcome"] == "replay_local_verifier_success"
    assert report["error"] is None
    assert report["planner"]["selected_skill"] == "interact_visible_object"
    assert report["planner"]["cited_evidence_ids"] == ["replay-shot-0001"]
    assert report["grounding"]["result"]["status"] == "grounded"
    assert report["task"]["target"]["evidence_ids"] == ["replay-shot-0001"]
    assert report["task"]["skill_contract"]["skill_name"] == "interact_visible_object"
    assert report["actions"] == [
        {
            "step_index": 0,
            "proposed_action": "confirm",
            "reason": "interaction_target_visible",
            "executed_on_backend": True,
            "blocked_reason": None,
            "evidence_ids": ["replay-shot-0001", "replay-shot-0002"],
            "sent_to_game": False,
        }
    ]
    assert report["dry_run_backend_actions"] == ["confirm"]
    assert report["verifier"]["scope"] == "replay-local"
    assert report["verifier"]["status"] == "success"
    assert report["verifier"]["evidence_ids"] == ["replay-shot-0001", "replay-shot-0002"]
    assert report["completion"]["status"] == "succeeded"
    assert report["observations"] == [
        {
            "index": 0,
            "screenshot_evidence_id": "replay-shot-0001",
            "transition": "recorded_initial_state",
            "caused_by_current_execution": False,
        },
        {
            "index": 1,
            "screenshot_evidence_id": "replay-shot-0002",
            "transition": "replayed_transition",
            "caused_by_current_execution": False,
        },
    ]
    assert report["budgets"]["used"] == {
        "task_attempts": 1,
        "primitive_action_attempts": 1,
        "observations": 2,
    }
    assert report["volatile_metadata_keys"] == ["generated_at", "paths"]
    events = [
        json.loads(line)
        for line in Path(report["paths"]["event_log"]).read_text(encoding="utf-8").splitlines()
    ]
    replay_evidence = [event for event in events if event["event_type"] == "evidence"]
    assert [event["payload"]["source"] for event in replay_evidence] == ["debug-replay"] * 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s["frames"][1]["payload"].update(screenshot_id="replay-shot-forged"),
        lambda s: (
            s["frames"][1].update(screenshot_evidence_id="replay-shot-0001")
            or s["frames"][1]["payload"].update(screenshot_id="replay-shot-0001")
        ),
        lambda s: s["frames"][1]["payload"].update(map_id=17),
        lambda s: s["frames"][0]["payload"].update(run_mode="debug"),
        lambda s: s.update(frames=[field_frame(f"shot-{index}") for index in range(5)]),
        lambda s: s.update(schema_version="2"),
        lambda s: s.update(unexpected=True),
    ],
    ids=[
        "mismatched-evidence",
        "duplicate-evidence",
        "hidden-state-field",
        "wrong-run-mode",
        "too-many-observations",
        "unknown-schema-version",
        "unknown-field",
    ],
)
def test_invalid_scenario_is_rejected_before_any_runtime_activity(
    tmp_path: Path,
    mutate: Any,
) -> None:
    scenario = base_scenario()
    mutate(scenario)
    report_path = tmp_path / "report.json"

    result = CliRunner().invoke(
        app,
        [
            "pilot-step",
            "--scenario",
            str(write_scenario(tmp_path, scenario)),
            "--report",
            str(report_path),
        ],
    )

    assert result.exit_code == 1
    assert not report_path.exists()
    assert not (tmp_path / "report-run").exists()


def test_existing_run_artifacts_fail_closed(tmp_path: Path) -> None:
    loaded, digest = load_pilot_step_scenario(SCENARIO_PATH)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(PilotStepScenarioError, match="already exists"):
        run_pilot_step(loaded, scenario_sha256=digest, run_dir=run_dir, stop_file=tmp_path / "STOP")


@pytest.mark.parametrize(
    ("mutate", "error_type"),
    [
        (
            lambda s: s["cortex_response"]["current_belief_state"][0].update(
                evidence_ids=["replay-shot-forged"]
            ),
            "PlannerOutputError",
        ),
        (lambda s: s["cortex_response"].pop("next_goal"), "ValidationError"),
        (
            lambda s: s["cortex_response"].update(selected_skill="continue_dialogue"),
            "PlannerOutputError",
        ),
        (
            lambda s: s["frames"][0]["payload"].update(
                visible_sprite_screen_positions=[],
                visible_sprite_visual_hashes=[],
            ),
            "ManagerGroundingError",
        ),
    ],
    ids=["forged-cortex-evidence", "malformed-cortex", "unavailable-skill", "ungroundable"],
)
def test_rejected_planning_or_grounding_sends_no_input(
    tmp_path: Path,
    mutate: Any,
    error_type: str,
) -> None:
    scenario = base_scenario()
    mutate(scenario)

    report, run = run_report(tmp_path, scenario)

    assert_non_official(report)
    assert report["outcome"] == "rejected"
    assert report["stop_reason"] == "rejected"
    assert report["error"]["type"] == error_type
    assert report["dry_run_backend_actions"] == []
    assert run.backend.actions == []
    assert report["budgets"]["used"]["primitive_action_attempts"] == 0
    assert report["budgets"]["used"]["observations"] == 1
    assert report["verifier"] is None


def test_command_has_no_real_input_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("real-input adapter must never be constructed")

    monkeypatch.setattr(xdotool_adapters.XdotoolInputBackend, "__init__", forbidden)
    monkeypatch.setattr(xdotool_adapters.XdotoolFocusGuard, "__init__", forbidden)

    report, run = run_report(tmp_path, base_scenario())

    assert type(run.backend) is DryRunInputBackend
    assert run.action_budget is not None
    assert type(run.action_budget.executor.backend) is DryRunInputBackend
    assert report["dry_run_backend_actions"] == ["confirm"]
    source = inspect.getsource(pilot_step_module)
    for forbidden_name in ("Xdotool", "xdotool", "subprocess", "allow_real_input", "socket"):
        assert forbidden_name not in source
    command = typer.main.get_command(app).commands["pilot-step"]  # type: ignore[attr-defined]
    option_names = {name for param in command.params for name in param.opts}
    assert option_names == {"--scenario", "--report", "--run-dir", "--stop-file"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_task_attempts": 2},
        {"max_action_attempts": 3},
        {"max_observations": 5},
        {"max_action_attempts": 0},
        {"max_observations": True},
    ],
)
def test_limits_cannot_widen_hard_bounds(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        PilotStepLimits(**kwargs)


def no_change_scenario() -> dict[str, Any]:
    scenario = base_scenario()
    scenario["frames"] = [
        field_frame("replay-shot-0001"),
        field_frame("replay-shot-0002"),
        field_frame("replay-shot-0003"),
    ]
    return scenario


def test_action_budget_fails_closed_before_extra_delegation(tmp_path: Path) -> None:
    report, run = run_report(
        tmp_path, no_change_scenario(), limits=PilotStepLimits(max_action_attempts=1)
    )

    assert report["outcome"] == "rejected"
    assert report["stop_reason"] == "budget_exceeded"
    assert report["error"]["type"] == "BridgeAssistedRuntimeBudgetExceeded"
    assert report["budgets"]["used"]["primitive_action_attempts"] == 1
    assert [action.value for action in run.backend.actions] == ["confirm"]


def test_observation_budget_fails_closed_before_extra_observation(tmp_path: Path) -> None:
    report, run = run_report(tmp_path, base_scenario(), limits=PilotStepLimits(max_observations=1))

    assert report["stop_reason"] == "budget_exceeded"
    assert report["budgets"]["used"] == {
        "task_attempts": 1,
        "primitive_action_attempts": 1,
        "observations": 1,
    }
    assert run.replay_source is not None
    assert len(run.replay_source.consumed) == 1


def test_default_bounds_hold_when_verifier_never_closes(tmp_path: Path) -> None:
    report, run = run_report(tmp_path, no_change_scenario())

    assert report["outcome"] == "manager_stop"
    assert report["completion"]["status"] == "timed_out"
    assert report["verifier"] is None
    assert report["budgets"]["used"] == {
        "task_attempts": 1,
        "primitive_action_attempts": 2,
        "observations": 3,
    }
    assert [action.value for action in run.backend.actions] == ["confirm", "confirm"]
    assert len(run.llm_client.requests) == 1
    assert_non_official(report)


def test_emergency_stop_blocks_every_action_and_further_tasks(tmp_path: Path) -> None:
    report, run = run_report(tmp_path, base_scenario(), stop=True)

    assert report["outcome"] == "manager_stop"
    assert report["stop_reason"] == "manager_stop"
    assert run.backend.actions == []
    assert report["actions"][0]["executed_on_backend"] is False
    assert report["actions"][0]["blocked_reason"] == "emergency_stop"
    assert report["completion"]["manager_stop"] is not None
    assert report["verifier"] is None
    assert report["budgets"]["used"]["task_attempts"] == 1
    assert report["budgets"]["used"]["observations"] == 1


def test_hash_only_change_is_not_verified_success(tmp_path: Path) -> None:
    scenario = base_scenario()
    scenario["frames"] = [
        field_frame("replay-shot-0001", "dhash:0123456789abcdef"),
        field_frame("replay-shot-0002", "dhash:fedcba9876543210"),
    ]

    report, _ = run_report(tmp_path, scenario)

    assert report["outcome"] != "replay_local_verifier_success"
    assert report["verifier"] is None or report["verifier"]["status"] != "success"
    assert_non_official(report)


def test_repeated_replay_yields_identical_semantic_report(tmp_path: Path) -> None:
    first, first_run = run_report(tmp_path, base_scenario(), run_name="first")
    second, second_run = run_report(tmp_path, base_scenario(), run_name="second")

    assert first_run.paths != second_run.paths
    assert semantic_report(first) == semantic_report(second)
    assert json.dumps(semantic_report(first), sort_keys=True) == json.dumps(
        semantic_report(second), sort_keys=True
    )


def test_semantic_report_excludes_only_declared_volatile_metadata(tmp_path: Path) -> None:
    report, run = run_report(tmp_path, base_scenario())
    full = pilot_step_module.with_volatile_metadata(copy.deepcopy(report), run)

    assert semantic_report(full) == report
