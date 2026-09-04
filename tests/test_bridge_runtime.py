import inspect
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import fh_agent.bridge_runtime as bridge_runtime_module
from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.bridge.evidence_sync import BridgeEvidenceSynchronizationError
from fh_agent.bridge.observation_source import BridgeRunModeMismatchError
from fh_agent.bridge.sanitizer import ForbiddenBridgeFieldError
from fh_agent.bridge_runtime import run_bridge_assisted_bounded
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.manager.event_sink import InMemoryManagerEventSink
from fh_agent.manager.grounded_cortex_submission import GroundedCortexTaskSubmitter
from fh_agent.manager.hierarchical_step import HierarchicalTaskStepRunner
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.replan_loop import (
    HierarchicalReplanLoopResult,
    HierarchicalReplanLoopRunner,
    ReplanLoopStepIds,
)
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.manager.target_ref import VisibleObjectTarget
from fh_agent.manager.task_executor import ManagerTaskExecutor
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.source import ObservationSourceExhausted
from fh_agent.planner.cortex import Cortex
from fh_agent.planner.llm_client import FakeLLMClient
from fh_agent.verifier.schemas import VerifierStatus


def append_payload(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("ab") as file:
        file.write(json.dumps(dict(payload)).encode("utf-8"))
        file.write(b"\n")


def dry_run_executor(backend: object) -> InputExecutor:
    return InputExecutor(
        target=WindowTarget(title="M-015 dry-run window"),
        focus_guard=FakeFocusGuard(focused=True),
        backend=backend,  # type: ignore[arg-type]
        min_interval_seconds=0.0,
    )


class RecordingLoopRunner:
    def __init__(self, result: HierarchicalReplanLoopResult) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []
        self.kwargs: list[dict[str, object]] = []

    def run_bounded(self, *args: object, **kwargs: object) -> HierarchicalReplanLoopResult:
        self.calls.append(args)
        self.kwargs.append(kwargs)
        return self.result


class SourceConsumingLoopRunner:
    def run_bounded(self, *args: object, **kwargs: object) -> HierarchicalReplanLoopResult:
        observation_source = args[1]
        observation_source.observe()  # type: ignore[attr-defined]
        return HierarchicalReplanLoopResult((), {}, "budget_exhausted")


class EvidenceHookBackend:
    def __init__(self, event_logger: EventLogger) -> None:
        self._event_logger = event_logger
        self.actions: list[PrimitiveAction] = []

    def send(self, action: PrimitiveAction) -> None:
        self.actions.append(action)
        if action is PrimitiveAction.CONFIRM:
            self._event_logger.append(
                "evidence",
                payload={"kind": "screenshot"},
                evidence_ids=["shot-after"],
            )


def bridge_payload(screenshot_id: str, *, run_mode: str = "bridge-assisted") -> dict[str, Any]:
    return {
        "run_mode": run_mode,
        "ui_state": "dialogue",
        "visible_message_text": "Visible line.",
        "screenshot_id": screenshot_id,
    }


def test_runtime_constructs_fixed_bridge_source_and_forwards_exact_inputs(tmp_path: Path) -> None:
    loop_result = HierarchicalReplanLoopResult((), {"retained": True}, "budget_exhausted")
    loop_runner = RecordingLoopRunner(loop_result)
    orchestrator = ManagerOrchestrator()
    executor = dry_run_executor(
        EvidenceHookBackend(EventLogger(tmp_path / "hook.jsonl", run_id="run-1"))
    )
    memory_summary = {"known_facts": []}
    step_ids = (ReplanLoopStepIds("task-1", "completion-1", "planner-1", "trace-1"),)
    feed_path = tmp_path / "feed.jsonl"
    event_path = tmp_path / "events.jsonl"

    result = run_bridge_assisted_bounded(  # type: ignore[arg-type]
        loop_runner,
        orchestrator,
        executor,
        memory_summary,
        run_id="run-1",
        feed_path=feed_path,
        event_log_path=event_path,
        step_ids=step_ids,
        created_at="2026-09-04T12:00:00+00:00",
    )

    call = loop_runner.calls[0]
    observation_source = call[1]
    assert call[0] is orchestrator
    assert call[2] is executor
    assert call[3] is memory_summary
    assert observation_source.__class__.__name__ == "BridgeObservationSource"
    assert observation_source._expected_run_mode == "bridge-assisted"  # type: ignore[attr-defined]
    assert loop_runner.kwargs[0] == {
        "run_id": "run-1",
        "step_ids": step_ids,
        "created_at": "2026-09-04T12:00:00+00:00",
    }
    assert result.run_id == "run-1"
    assert result.feed_path is feed_path
    assert result.event_log_path is event_path
    assert result.loop_result is loop_result
    assert not feed_path.exists()


@pytest.mark.parametrize(
    ("payload", "error_type"),
    [
        (bridge_payload("shot-1"), BridgeEvidenceSynchronizationError),
        (
            {"run_mode": "bridge-assisted", "screenshot_id": "shot-1", "map_id": 17},
            ForbiddenBridgeFieldError,
        ),
        (bridge_payload("shot-1", run_mode="debug"), BridgeRunModeMismatchError),
    ],
)
def test_existing_bridge_failures_propagate_without_runtime_translation(
    tmp_path: Path,
    payload: Mapping[str, Any],
    error_type: type[ValueError],
) -> None:
    feed_path = tmp_path / "feed.jsonl"
    append_payload(feed_path, payload)
    executor = dry_run_executor(
        EvidenceHookBackend(EventLogger(tmp_path / "hook.jsonl", run_id="run-1"))
    )

    with pytest.raises(error_type):
        run_bridge_assisted_bounded(  # type: ignore[arg-type]
            SourceConsumingLoopRunner(),
            ManagerOrchestrator(),
            executor,
            {},
            run_id="run-1",
            feed_path=feed_path,
            event_log_path=tmp_path / "events.jsonl",
            step_ids=(ReplanLoopStepIds("task-1", "completion-1"),),
        )


def test_missing_feed_propagates_existing_observation_exhaustion(tmp_path: Path) -> None:
    with pytest.raises(ObservationSourceExhausted):
        run_bridge_assisted_bounded(  # type: ignore[arg-type]
            SourceConsumingLoopRunner(),
            ManagerOrchestrator(),
            dry_run_executor(
                EvidenceHookBackend(EventLogger(tmp_path / "hook.jsonl", run_id="run-1"))
            ),
            {},
            run_id="run-1",
            feed_path=tmp_path / "missing.jsonl",
            event_log_path=tmp_path / "events.jsonl",
            step_ids=(ReplanLoopStepIds("task-1", "completion-1"),),
        )


def test_jsonl_runtime_completes_one_hierarchical_dry_run_step(tmp_path: Path) -> None:
    feed_path = tmp_path / "feed.jsonl"
    event_path = tmp_path / "events.jsonl"
    event_logger = EventLogger(event_path, run_id="run-1")
    event_logger.append("evidence", payload={"kind": "screenshot"}, evidence_ids=["shot-before"])
    append_payload(
        feed_path,
        {
            "run_mode": "bridge-assisted",
            "ui_state": "field",
            "visible_sprite_screen_positions": [[120, 80]],
            "visible_sprite_visual_hashes": ["dhash:0123456789abcdef"],
            "screenshot_id": "shot-before",
        },
    )
    append_payload(
        feed_path,
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "Visible interaction outcome.",
            "screenshot_id": "shot-after",
        },
    )
    planner_payload = {
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
    client = FakeLLMClient(responses=[json.dumps(planner_payload)])
    sink = InMemoryManagerEventSink()
    orchestrator = ManagerOrchestrator(event_sink=sink)
    backend = EvidenceHookBackend(event_logger)
    task_executor = ManagerTaskExecutor(skill_runner=SkillRunner(event_logger=event_logger))
    loop_runner = HierarchicalReplanLoopRunner(
        HierarchicalTaskStepRunner(
            GroundedCortexTaskSubmitter(Cortex(client)),
            task_executor=task_executor,
        )
    )

    result = run_bridge_assisted_bounded(
        loop_runner,
        orchestrator,
        dry_run_executor(backend),
        {},
        run_id="run-1",
        feed_path=feed_path,
        event_log_path=event_path,
        step_ids=(ReplanLoopStepIds("task-1", "completion-1", "planner-1", "trace-1"),),
        created_at="2026-09-04T12:00:00+00:00",
    )

    step_result = result.loop_result.step_results[0]
    completion = step_result.execution_result.completion_event
    grounding_result = step_result.submission_result.grounding_result
    assert len(client.requests) == 1
    assert backend.actions == [PrimitiveAction.CONFIRM]
    assert len(result.loop_result.step_results) == 1
    assert result.loop_result.stop_reason == "budget_exhausted"
    assert completion is not None
    assert grounding_result is not None
    assert step_result.planning_observation.evidence_ids == ["shot-before"]
    assert step_result.submission_result.grounding_request is not None
    assert step_result.submission_result.grounding_request.evidence_scope_ids == ("shot-before",)
    assert isinstance(grounding_result.target, VisibleObjectTarget)
    assert "shot-before" in grounding_result.target.evidence_ids
    action_result = step_result.execution_result.skill_run_result.action_execution_results[0]
    assert action_result.evidence_ids == [
        "shot-before",
        "shot-after",
    ]
    assert completion.verifier_result is not None
    assert completion.verifier_result.status is VerifierStatus.SUCCESS
    assert completion.verifier_result.evidence_ids == ["shot-before", "shot-after"]
    assert completion.completion_evidence_ids == ["shot-before", "shot-after"]
    assert completion.status.value == "succeeded"
    assert isinstance(completion.target, VisibleObjectTarget)
    assert orchestrator.scheduler.current_task is None
    assert len(sink.list_task_completions()) == 1


def test_runtime_module_has_only_composition_dependencies() -> None:
    source = inspect.getsource(bridge_runtime_module)

    for forbidden in (
        "Cortex",
        "LLMClient",
        "GroundedCortexTaskSubmitter",
        "SkillRunner",
        "SkillCatalog",
        "VerifierCatalog",
        "PrimitiveAction",
        "GroundingService",
        "sanitize_bridge_payload",
        "VisibleBridgeAdapter",
        "EventLogger",
        "EvidenceStore",
        "ScreenCapture",
        "DryRunInputBackend",
        "xdotool",
        "socket",
        "http",
        "asyncio",
        "threading",
        "subprocess",
        "sleep(",
    ):
        assert forbidden not in source
