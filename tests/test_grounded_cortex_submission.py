import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

import fh_agent.manager.grounded_cortex_submission as submission_module
from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.observation_source import (
    BridgeObservationSource,
    BridgePayloadSourceExhausted,
)
from fh_agent.manager.grounded_cortex_submission import GroundedCortexTaskSubmitter
from fh_agent.manager.grounding import GroundingRequest
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskStatus
from fh_agent.manager.target_ref import (
    GroundingResult,
    VisibleObjectTarget,
    VisibleScreenPointTarget,
)
from fh_agent.manager.task_manager import ManagerGroundingError
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation, VisibleSprite
from fh_agent.planner.cortex import Cortex
from fh_agent.planner.llm_client import FakeLLMClient
from fh_agent.planner.planner_output import PlannerOutput, PlannerOutputError
from fh_agent.skill_capabilities import SkillCapabilityContract, UniversalSkillName


class RecordingPlanner:
    def __init__(self, output: PlannerOutput) -> None:
        self.output = output
        self.calls: list[
            tuple[Observation, Mapping[str, Any], Sequence[UniversalSkillName] | None]
        ] = []

    def plan_next_goal(
        self,
        observation: Observation,
        memory_summary: Mapping[str, Any],
        *,
        available_skills: Sequence[UniversalSkillName] | None = None,
    ) -> PlannerOutput:
        self.calls.append((observation, memory_summary, available_skills))
        return self.output


class RecordingGroundingService:
    def __init__(self, result: GroundingResult) -> None:
        self.result = result
        self.calls: list[tuple[GroundingRequest, Observation]] = []

    def ground(self, request: GroundingRequest, observation: Observation) -> GroundingResult:
        self.calls.append((request, observation))
        return self.result


class EvidenceRecordingBridgePayloadSource:
    def __init__(self, event_logger: EventLogger, payload: Mapping[str, Any]) -> None:
        self._event_logger = event_logger
        self._payload = payload
        self.next_payload_calls = 0

    def next_payload(self) -> Mapping[str, Any]:
        self.next_payload_calls += 1
        if self.next_payload_calls > 1:
            raise BridgePayloadSourceExhausted
        screenshot_id = self._payload.get("screenshot_id")
        if isinstance(screenshot_id, str):
            self._event_logger.append(
                "evidence",
                payload={"kind": "screenshot"},
                evidence_ids=[screenshot_id],
            )
        return self._payload


def planner_output(
    *,
    selected_skill: str = "continue_dialogue",
    evidence_ids: list[str] | None = None,
    next_goal: str = "Continue the visible dialogue.",
) -> PlannerOutput:
    return PlannerOutput.model_validate(
        {
            "current_belief_state": [
                {
                    "kind": "fact",
                    "claim": "Visible evidence supports the next goal.",
                    "evidence_ids": evidence_ids or ["shot-current"],
                }
            ],
            "open_questions": [],
            "next_goal": next_goal,
            "selected_skill": selected_skill,
            "success_condition": ["visible_change"],
            "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
            "memory_updates_requested": [],
        }
    )


def observation(
    *,
    evidence_ids: list[str] | None = None,
    sprites: list[VisibleSprite] | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="field",
        screenshot_id="shot-current",
        evidence_ids=["shot-current"] if evidence_ids is None else evidence_ids,
        visible_sprites=[] if sprites is None else sprites,
    )


def visible_object_result() -> GroundingResult:
    return GroundingResult(
        status="grounded",
        target=VisibleObjectTarget(
            target_id="visible-object-1",
            confidence=0.9,
            evidence_ids=("shot-current", "sprite-current"),
            screen_position=(120, 80),
            visual_hash="dhash:0123456789abcdef",
        ),
        evidence_ids=("shot-current", "sprite-current"),
    )


def test_targetless_submission_forwards_planning_inputs_without_grounding() -> None:
    output = planner_output()
    planner = RecordingPlanner(output)
    grounding_service = RecordingGroundingService(visible_object_result())
    capabilities = SkillCapabilityContract(available_skills=("continue_dialogue",))
    orchestrator = ManagerOrchestrator(runtime_capabilities=capabilities)
    current_observation = observation()
    memory_summary = {"known_facts": [{"claim": "Visible fact.", "evidence_ids": ["shot-current"]}]}

    result = GroundedCortexTaskSubmitter(
        planner,
        grounding_service=grounding_service,
    ).plan_ground_and_submit(
        orchestrator,
        current_observation,
        memory_summary,
        task_id="task-targetless",
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
    )

    planned_observation, planned_memory, available_skills = planner.calls[0]
    assert planned_observation is current_observation
    assert planned_memory is memory_summary
    assert available_skills is capabilities.available_skills
    assert result.planner_output is output
    assert result.grounding_request is None
    assert result.grounding_result is None
    assert grounding_service.calls == []
    assert result.scheduled_task.status is TaskStatus.PENDING
    assert result.scheduled_task.task_spec.task_id == "task-targetless"
    assert result.scheduled_task.task_spec.selected_skill == "continue_dialogue"
    assert result.scheduled_task.task_spec.target is None
    assert result.scheduled_task.task_spec.planner_output_id == "planner-output-1"
    assert result.scheduled_task.task_spec.planner_trace_id == "planner-trace-1"
    assert orchestrator.scheduler.current_task is None
    assert orchestrator.scheduler.queued_tasks == (result.scheduled_task,)


def test_target_required_submission_uses_current_evidence_and_preserves_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = planner_output(
        selected_skill="interact_visible_object",
        evidence_ids=["shot-prior", "shot-current"],
        next_goal="Interact with the visible object.",
    )
    planner = RecordingPlanner(output)
    grounding_service = RecordingGroundingService(visible_object_result())
    orchestrator = ManagerOrchestrator()
    current_observation = observation(evidence_ids=["shot-current"])
    captured: dict[str, object] = {}
    original_submit = orchestrator.submit_planner_output

    def record_submit(submitted_output: PlannerOutput, **kwargs: object):
        captured["planner_output"] = submitted_output
        captured.update(kwargs)
        return original_submit(submitted_output, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(orchestrator, "submit_planner_output", record_submit)

    result = GroundedCortexTaskSubmitter(
        planner,
        grounding_service=grounding_service,
    ).plan_ground_and_submit(
        orchestrator,
        current_observation,
        {},
        task_id="task-targeted",
        planner_output_id="planner-output-2",
        planner_trace_id="planner-trace-2",
    )

    assert result.planner_output is output
    assert result.grounding_request is grounding_service.calls[0][0]
    assert result.grounding_result is grounding_service.result
    assert result.grounding_request.selected_skill == "interact_visible_object"
    assert result.grounding_request.semantic_goal == output.next_goal
    assert result.grounding_request.evidence_scope_ids == ("shot-current",)
    assert grounding_service.calls[0][1] is current_observation
    assert captured["planner_output"] is output
    assert captured["grounding_result"] is result.grounding_result
    assert captured["task_id"] == "task-targeted"
    assert captured["planner_output_id"] == "planner-output-2"
    assert captured["planner_trace_id"] == "planner-trace-2"
    assert result.scheduled_task.status is TaskStatus.PENDING
    assert result.scheduled_task.task_spec.target is result.grounding_result.target
    assert result.scheduled_task.task_spec.planner_output_id == "planner-output-2"
    assert result.scheduled_task.task_spec.planner_trace_id == "planner-trace-2"
    assert orchestrator.scheduler.current_task is None
    assert orchestrator.scheduler.queued_tasks == (result.scheduled_task,)


@pytest.mark.parametrize(
    ("result", "expected_code"),
    [
        (
            GroundingResult(
                status="grounding_failed",
                failure_reason="insufficient_evidence",
                evidence_ids=(),
            ),
            "grounding_failed",
        ),
        (
            GroundingResult(
                status="grounded",
                target=VisibleScreenPointTarget(
                    target_id="point-1",
                    confidence=0.9,
                    evidence_ids=("shot-current",),
                    screen_position=(10, 20),
                ),
                evidence_ids=("shot-current",),
            ),
            "incompatible_target_type",
        ),
    ],
)
def test_manager_rejects_failed_or_incompatible_grounding_result(
    result: GroundingResult,
    expected_code: str,
) -> None:
    grounding_service = RecordingGroundingService(result)
    orchestrator = ManagerOrchestrator()

    with pytest.raises(ManagerGroundingError) as exc_info:
        GroundedCortexTaskSubmitter(
            RecordingPlanner(planner_output(selected_skill="interact_visible_object")),
            grounding_service=grounding_service,
        ).plan_ground_and_submit(
            orchestrator,
            observation(),
            {},
            task_id="task-rejected",
        )

    assert exc_info.value.error_code == expected_code
    assert len(grounding_service.calls) == 1
    assert orchestrator.scheduler.queued_tasks == ()
    assert orchestrator.scheduler.current_task is None


def test_empty_and_ambiguous_visible_evidence_reach_existing_manager_rejection() -> None:
    empty_orchestrator = ManagerOrchestrator()
    with pytest.raises(ManagerGroundingError) as empty_error:
        GroundedCortexTaskSubmitter(
            RecordingPlanner(planner_output(selected_skill="interact_visible_object"))
        ).plan_ground_and_submit(
            empty_orchestrator,
            observation(evidence_ids=[]),
            {},
            task_id="task-empty",
        )

    ambiguous_orchestrator = ManagerOrchestrator()
    sprites = [
        VisibleSprite(screen_position=(10, 20), confidence=0.9, evidence_id="sprite-1"),
        VisibleSprite(screen_position=(30, 40), confidence=0.9, evidence_id="sprite-2"),
    ]
    with pytest.raises(ManagerGroundingError) as ambiguous_error:
        GroundedCortexTaskSubmitter(
            RecordingPlanner(planner_output(selected_skill="interact_visible_object"))
        ).plan_ground_and_submit(
            ambiguous_orchestrator,
            observation(sprites=sprites),
            {},
            task_id="task-ambiguous",
        )

    assert empty_error.value.failure_reason == "insufficient_evidence"
    assert ambiguous_error.value.failure_reason == "ambiguous_candidates"
    assert empty_orchestrator.scheduler.queued_tasks == ()
    assert ambiguous_orchestrator.scheduler.queued_tasks == ()


def test_fabricated_cortex_evidence_rejects_before_grounding_or_submission() -> None:
    output = planner_output(selected_skill="interact_visible_object", evidence_ids=["fabricated"])
    cortex = Cortex(FakeLLMClient(responses=[json.dumps(output.model_dump(mode="json"))]))
    grounding_service = RecordingGroundingService(visible_object_result())
    orchestrator = ManagerOrchestrator()

    with pytest.raises(PlannerOutputError, match="fabricated"):
        GroundedCortexTaskSubmitter(
            cortex,
            grounding_service=grounding_service,
        ).plan_ground_and_submit(
            orchestrator,
            observation(),
            {},
            task_id="task-fabricated",
        )

    assert len(cortex.llm_client.requests) == 1
    assert grounding_service.calls == []
    assert orchestrator.scheduler.queued_tasks == ()
    assert orchestrator.scheduler.current_task is None


def test_synchronized_bridge_observation_reaches_pending_grounded_manager_task(
    tmp_path: Path,
) -> None:
    event_log_path = tmp_path / "events.jsonl"
    payload_source = EvidenceRecordingBridgePayloadSource(
        EventLogger(event_log_path, run_id="run-1"),
        {
            "run_mode": "bridge-assisted",
            "ui_state": "field",
            "visible_sprite_screen_positions": [[120, 80]],
            "visible_sprite_visual_hashes": ["dhash:0123456789abcdef"],
            "screenshot_id": "shot-1",
        },
    )
    bridge_source = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
    )
    bridge_observation = bridge_source.observe()
    output = planner_output(
        selected_skill="interact_visible_object",
        evidence_ids=["shot-1"],
        next_goal="Interact with the visible object.",
    )
    cortex = Cortex(FakeLLMClient(responses=[json.dumps(output.model_dump(mode="json"))]))
    orchestrator = ManagerOrchestrator()

    result = GroundedCortexTaskSubmitter(cortex).plan_ground_and_submit(
        orchestrator,
        bridge_observation,
        {},
        task_id="task-bridge",
    )

    assert payload_source.next_payload_calls == 1
    assert bridge_observation.evidence_ids == ["shot-1"]
    assert len(bridge_observation.visible_sprites) == 1
    assert bridge_observation.visible_sprites[0].evidence_id == "shot-1"
    assert len(cortex.llm_client.requests) == 1
    assert result.planner_output.selected_skill == "interact_visible_object"
    assert result.grounding_request is not None
    assert result.grounding_request.selected_skill == "interact_visible_object"
    assert result.grounding_request.semantic_goal == result.planner_output.next_goal
    assert result.grounding_request.evidence_scope_ids == ("shot-1",)
    assert result.grounding_result is not None
    assert result.grounding_result.status == "grounded"
    assert isinstance(result.grounding_result.target, VisibleObjectTarget)
    assert "shot-1" in result.grounding_result.target.evidence_ids
    assert result.scheduled_task.status is TaskStatus.PENDING
    assert result.scheduled_task.task_spec.selected_skill == "interact_visible_object"
    assert result.scheduled_task.task_spec.target is result.grounding_result.target
    assert orchestrator.scheduler.current_task is None
    assert orchestrator.scheduler.queued_tasks == (result.scheduled_task,)


def test_submission_module_has_no_execution_or_runtime_dependencies() -> None:
    source = Path(submission_module.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "ManagerTaskExecutor",
        "SkillRunner",
        "SkillCatalog",
        "VerifierCatalog",
        "InputExecutor",
        "PrimitiveAction",
        "fh_agent.bridge",
        "EventLogger",
        "MemoryDB",
        "start_next(",
        ".execute(",
        ".verify(",
    ):
        assert forbidden not in source
