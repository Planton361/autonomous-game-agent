import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.bridge.sanitizer import ForbiddenBridgeFieldError
from fh_agent.bridge.snapshot_response import BridgeSnapshotResponseError
from fh_agent.bridge_assisted_runtime import (
    BRIDGE_ASSISTED_RUN_MODE,
    BoundedSnapshotObservationSource,
    BridgeAssistedRuntimeBudgetExceeded,
    BridgeAssistedRuntimeConfig,
    BridgeAssistedRuntimeLimits,
    assemble_bridge_assisted_runtime,
)
from fh_agent.game.emergency_stop import StopFileEmergencyStopCheck
from fh_agent.game.input_executor import DryRunInputBackend
from fh_agent.game.window import WindowTarget
from fh_agent.game.xdotool_adapters import XdotoolFocusGuard, XdotoolInputBackend
from fh_agent.manager.event_sink import InMemoryManagerEventSink
from fh_agent.manager.replan_loop import ReplanLoopStepIds
from fh_agent.memory.event_log import EventLogger
from fh_agent.memory.evidence import EvidenceStore
from fh_agent.observation.schemas import Observation
from fh_agent.perception.screen_capture import DummyScreenCapture
from fh_agent.perception.subprocess_capture import SubprocessPpmScreenCapture
from fh_agent.planner.llm_client import FakeLLMClient, OpenAICompatibleLLMClient
from fh_agent.verifier.schemas import VerifierStatus


class SyntheticBridgeResponseWaiter:
    def __init__(self, *payloads: Mapping[str, Any]) -> None:
        self.payloads = [dict(payload) for payload in payloads]
        self.calls: list[Path] = []

    def wait_for_response(self, response_path: Path) -> None:
        self.calls.append(response_path)
        if not self.payloads:
            raise AssertionError("no synthetic bridge response queued")
        request_path = response_path.with_name(
            response_path.name.replace(".response.json", ".request.json")
        )
        request = json.loads(request_path.read_text(encoding="utf-8"))
        payload = self.payloads.pop(0)
        payload.setdefault("run_mode", request["run_mode"])
        payload.setdefault("screenshot_id", request["screenshot_id"])
        response_path.write_text(
            json.dumps(
                {
                    "request_id": request["request_id"],
                    "run_id": request["run_id"],
                    "payload": payload,
                }
            )
            + "\n",
            encoding="utf-8",
        )


class StaticObservationSource:
    def __init__(self) -> None:
        self.calls = 0

    def observe(self) -> Observation:
        self.calls += 1
        return Observation(run_id="run-1", evidence_ids=[f"shot-{self.calls}"])


def config_for_test(
    tmp_path: Path,
    *,
    limits: BridgeAssistedRuntimeLimits | None = None,
    allow_real_input: bool = False,
    local_llm_base_url: str = "http://127.0.0.1:8080/v1",
) -> BridgeAssistedRuntimeConfig:
    return BridgeAssistedRuntimeConfig(
        run_id="run-1",
        exchange_directory=tmp_path / "exchange",
        feed_path=tmp_path / "feed" / "bridge.jsonl",
        event_log_path=tmp_path / "runs" / "run-1" / "events.jsonl",
        screenshots_root=tmp_path / "screenshots",
        stop_file_path=tmp_path / "runs" / "run-1" / "STOP",
        local_llm_base_url=local_llm_base_url,
        local_llm_model="local-test-model",
        target_window=WindowTarget(title="Fear & Hunger"),
        limits=limits or BridgeAssistedRuntimeLimits(),
        key_bindings={PrimitiveAction.CONFIRM: "Return"},
        allow_real_input=allow_real_input,
        input_min_interval_seconds=0.0,
    )


def prepare_bridge_paths(config: BridgeAssistedRuntimeConfig) -> None:
    config.exchange_directory.mkdir(parents=True)
    config.feed_path.parent.mkdir(parents=True)


def deterministic_evidence_store(tmp_path: Path, *evidence_ids: str) -> EvidenceStore:
    ids = iter(evidence_ids)
    return EvidenceStore(
        tmp_path / "screenshots",
        run_id="run-1",
        id_factory=lambda: next(ids),
    )


def planner_payload() -> dict[str, Any]:
    return {
        "current_belief_state": [
            {
                "kind": "fact",
                "claim": "One visible object candidate is present.",
                "evidence_ids": ["shot-before"],
            }
        ],
        "open_questions": [],
        "next_goal": "Interact with the visible object.",
        "selected_skill": "interact_visible_object",
        "success_condition": ["visible_interaction"],
        "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
        "memory_updates_requested": [],
    }


def test_assembly_has_no_runtime_side_effects_and_defaults_to_dry_input(tmp_path: Path) -> None:
    config = config_for_test(tmp_path)
    capture = SubprocessPpmScreenCapture(("visible-capture", "--ppm"))

    runtime = assemble_bridge_assisted_runtime(config, capture=capture)

    assert runtime.run_mode == BRIDGE_ASSISTED_RUN_MODE
    assert isinstance(runtime.llm_client, OpenAICompatibleLLMClient)
    assert isinstance(runtime.input_backend, DryRunInputBackend)
    assert runtime.input_executor.attempt_count == 0
    assert runtime.observation_source.attempt_count == 0
    assert not config.exchange_directory.exists()
    assert not config.feed_path.exists()
    assert not config.event_log_path.exists()
    assert not config.stop_file_path.exists()
    assert not config.screenshots_root.exists()


def test_real_input_construction_requires_explicit_flag_and_uses_guarded_xdotool(
    tmp_path: Path,
) -> None:
    config = config_for_test(tmp_path, allow_real_input=True)
    runtime = assemble_bridge_assisted_runtime(
        config,
        capture=DummyScreenCapture(),
        llm_client=FakeLLMClient(responses=[]),
    )

    assert isinstance(runtime.focus_guard, XdotoolFocusGuard)
    assert isinstance(runtime.input_backend, XdotoolInputBackend)
    assert isinstance(
        runtime.input_executor.executor.emergency_stop_check,
        StopFileEmergencyStopCheck,
    )
    assert runtime.input_executor.executor.min_interval_seconds == 0.0
    assert runtime.input_executor.attempt_count == 0


def test_non_loopback_cortex_endpoint_is_rejected_before_runtime_activity(tmp_path: Path) -> None:
    config = config_for_test(tmp_path, local_llm_base_url="https://api.example.com/v1")
    capture = DummyScreenCapture()

    with pytest.raises(ValueError, match="loopback"):
        assemble_bridge_assisted_runtime(
            config,
            capture=capture,
            llm_client=FakeLLMClient(responses=[]),
        )

    assert capture.capture_count == 0
    assert not config.event_log_path.exists()


def test_task_budget_rejects_oversized_plan_before_first_observation(tmp_path: Path) -> None:
    config = config_for_test(
        tmp_path,
        limits=BridgeAssistedRuntimeLimits(
            max_task_attempts=1,
            max_action_attempts=3,
            max_snapshot_attempts=4,
        ),
    )
    capture = DummyScreenCapture()
    runtime = assemble_bridge_assisted_runtime(
        config,
        capture=capture,
        llm_client=FakeLLMClient(responses=[]),
    )

    with pytest.raises(BridgeAssistedRuntimeBudgetExceeded, match="task-attempt"):
        runtime.run_bounded(
            {},
            step_ids=(
                ReplanLoopStepIds("task-1", "completion-1"),
                ReplanLoopStepIds("task-2", "completion-2"),
            ),
        )

    assert capture.capture_count == 0
    assert runtime.input_executor.attempt_count == 0
    assert runtime.observation_source.attempt_count == 0


def test_action_budget_fails_closed_before_second_delegate(tmp_path: Path) -> None:
    config = config_for_test(
        tmp_path,
        limits=BridgeAssistedRuntimeLimits(
            max_task_attempts=1,
            max_action_attempts=1,
            max_snapshot_attempts=3,
        ),
    )
    runtime = assemble_bridge_assisted_runtime(
        config,
        capture=DummyScreenCapture(),
        llm_client=FakeLLMClient(responses=[]),
    )

    first = runtime.input_executor.execute(PrimitiveAction.WAIT)
    assert first.executed is True
    with pytest.raises(BridgeAssistedRuntimeBudgetExceeded, match="primitive action"):
        runtime.input_executor.execute(PrimitiveAction.WAIT)

    assert runtime.input_executor.attempt_count == 1
    assert isinstance(runtime.input_backend, DryRunInputBackend)
    assert runtime.input_backend.actions == [PrimitiveAction.WAIT]


def test_snapshot_budget_fails_closed_before_second_source_call() -> None:
    source = StaticObservationSource()
    bounded = BoundedSnapshotObservationSource(source, max_attempts=1)

    assert bounded.observe().evidence_ids == ["shot-1"]
    with pytest.raises(BridgeAssistedRuntimeBudgetExceeded, match="snapshot"):
        bounded.observe()

    assert bounded.attempt_count == 1
    assert source.calls == 1


@pytest.mark.parametrize(
    "limits",
    [
        BridgeAssistedRuntimeLimits(
            max_task_attempts=1,
            max_action_attempts=1,
            max_snapshot_attempts=1,
        ),
    ],
)
def test_positive_runtime_limits_are_accepted(limits: BridgeAssistedRuntimeLimits) -> None:
    assert limits.max_task_attempts == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_task_attempts": 0},
        {"max_action_attempts": 0},
        {"max_snapshot_attempts": 0},
        {"max_task_attempts": True},
    ],
)
def test_runtime_limits_must_be_positive_integers(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        BridgeAssistedRuntimeLimits(**kwargs)  # type: ignore[arg-type]


def test_synchronized_runtime_closes_one_full_hierarchical_dry_run_cycle(tmp_path: Path) -> None:
    config = config_for_test(
        tmp_path,
        limits=BridgeAssistedRuntimeLimits(
            max_task_attempts=1,
            max_action_attempts=3,
            max_snapshot_attempts=3,
        ),
    )
    prepare_bridge_paths(config)
    waiter = SyntheticBridgeResponseWaiter(
        {
            "ui_state": "field",
            "visible_sprite_screen_positions": [[120, 80]],
            "visible_sprite_visual_hashes": ["dhash:0123456789abcdef"],
        },
        {
            "ui_state": "dialogue",
            "visible_message_text": "Visible interaction outcome.",
        },
    )
    client = FakeLLMClient(responses=[json.dumps(planner_payload())])
    sink = InMemoryManagerEventSink()
    logger = EventLogger(config.event_log_path, run_id=config.run_id)
    runtime = assemble_bridge_assisted_runtime(
        config,
        capture=DummyScreenCapture(),
        llm_client=client,
        response_waiter=waiter,
        manager_event_sink=sink,
        event_logger=logger,
        evidence_store=deterministic_evidence_store(tmp_path, "shot-before", "shot-after"),
    )

    result = runtime.run_bounded(
        {},
        step_ids=(ReplanLoopStepIds("task-1", "completion-1", "planner-1", "trace-1"),),
        created_at="2026-09-07T00:00:00+00:00",
    )

    step = result.loop_result.step_results[0]
    completion = step.execution_result.completion_event
    assert result.run_mode == "bridge-assisted"
    assert result.task_attempts == 1
    assert result.action_attempts == 1
    assert result.snapshot_attempts == 2
    assert result.loop_result.stop_reason == "budget_exhausted"
    assert len(client.requests) == 1
    assert len(waiter.calls) == 2
    assert isinstance(runtime.input_backend, DryRunInputBackend)
    assert runtime.input_backend.actions == [PrimitiveAction.CONFIRM]
    assert step.planning_observation.evidence_ids == ["shot-before"]
    assert completion is not None
    assert completion.status.value == "succeeded"
    assert completion.verifier_result is not None
    assert completion.verifier_result.status is VerifierStatus.SUCCESS
    assert completion.verifier_result.evidence_ids == ["shot-before", "shot-after"]
    assert completion.planner_output_id == "planner-1"
    assert completion.planner_trace_id == "trace-1"
    assert len(sink.list_task_completions()) == 1
    event_types = [event.event_type for event in logger.read_all()]
    assert event_types.count("evidence") == 2
    assert "action_result" in event_types
    assert "verifier_result" in event_types
    assert "verified_reward" in event_types


def test_hidden_state_response_is_rejected_by_existing_sanitizer(tmp_path: Path) -> None:
    config = config_for_test(tmp_path)
    prepare_bridge_paths(config)
    runtime = assemble_bridge_assisted_runtime(
        config,
        capture=DummyScreenCapture(),
        llm_client=FakeLLMClient(responses=[]),
        response_waiter=SyntheticBridgeResponseWaiter({"ui_state": "field", "map_id": 7}),
        evidence_store=deterministic_evidence_store(tmp_path, "shot-1"),
    )

    with pytest.raises(ForbiddenBridgeFieldError):
        runtime.observation_source.observe()


def test_bridge_mode_mismatch_is_rejected_by_existing_correlation_boundary(tmp_path: Path) -> None:
    config = config_for_test(tmp_path)
    prepare_bridge_paths(config)
    runtime = assemble_bridge_assisted_runtime(
        config,
        capture=DummyScreenCapture(),
        llm_client=FakeLLMClient(responses=[]),
        response_waiter=SyntheticBridgeResponseWaiter(
            {"run_mode": "debug", "ui_state": "field"}
        ),
        evidence_store=deterministic_evidence_store(tmp_path, "shot-1"),
    )

    with pytest.raises(BridgeSnapshotResponseError, match="run_mode"):
        runtime.observation_source.observe()
