import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

import fh_agent.manager.cortex_submission as cortex_submission_module
from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.observation_source import (
    BridgeObservationSource,
    BridgePayloadSourceExhausted,
)
from fh_agent.manager.cortex_submission import CortexTaskSubmitter
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import ScheduledTask, TaskStatus
from fh_agent.manager.target_ref import GroundingResult, VisibleScreenPointTarget
from fh_agent.manager.task_manager import ManagerGroundingError, TaskManagerError
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation
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
) -> PlannerOutput:
    return PlannerOutput.model_validate(
        {
            "current_belief_state": [
                {
                    "kind": "fact",
                    "claim": "Visible dialogue is present.",
                    "evidence_ids": evidence_ids or ["shot-1"],
                }
            ],
            "open_questions": [],
            "next_goal": "Continue the visible dialogue.",
            "selected_skill": selected_skill,
            "success_condition": ["visible_text_changed"],
            "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
            "memory_updates_requested": [],
        }
    )


def observation() -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text="Visible dialogue.",
        screenshot_id="shot-1",
        evidence_ids=["shot-1"],
    )


def test_submitter_forwards_exact_planning_inputs_and_manager_capabilities() -> None:
    output = planner_output()
    planner = RecordingPlanner(output)
    capabilities = SkillCapabilityContract(available_skills=("continue_dialogue",))
    orchestrator = ManagerOrchestrator(runtime_capabilities=capabilities)
    memory_summary = {"known_facts": [{"claim": "Visible dialogue.", "evidence_ids": ["shot-1"]}]}
    input_observation = observation()

    result = CortexTaskSubmitter(planner).plan_and_submit(
        orchestrator,
        input_observation,
        memory_summary,
        task_id="task-1",
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
    )

    planned_observation, planned_memory, available_skills = planner.calls[0]
    assert planned_observation is input_observation
    assert planned_memory is memory_summary
    assert available_skills is capabilities.available_skills
    assert result.planner_output is output
    assert result.scheduled_task.status is TaskStatus.PENDING
    assert result.scheduled_task.task_spec.task_id == "task-1"
    assert result.scheduled_task.task_spec.selected_skill == "continue_dialogue"
    assert result.scheduled_task.task_spec.target is None
    assert result.scheduled_task.task_spec.source_evidence_ids == ["shot-1"]
    assert result.scheduled_task.task_spec.planner_output_id == "planner-output-1"
    assert result.scheduled_task.task_spec.planner_trace_id == "planner-trace-1"
    assert orchestrator.scheduler.current_task is None
    assert orchestrator.scheduler.queued_tasks == (result.scheduled_task,)
    assert orchestrator.scheduler.queued_tasks[0] is result.scheduled_task


def test_submitter_passes_exact_output_and_grounding_to_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = planner_output(selected_skill="basic_reach_target")
    planner = RecordingPlanner(output)
    orchestrator = ManagerOrchestrator()
    grounding = GroundingResult(
        status="grounded",
        target=VisibleScreenPointTarget(
            target_id="visible-point-1",
            confidence=0.9,
            evidence_ids=("shot-1",),
            screen_position=(10, 20),
        ),
        evidence_ids=("shot-1",),
    )
    captured: dict[str, object] = {}
    original_submit = orchestrator.submit_planner_output

    def record_submit(
        submitted_output: PlannerOutput,
        **kwargs: object,
    ) -> ScheduledTask:
        captured["output"] = submitted_output
        captured.update(kwargs)
        return original_submit(submitted_output, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(orchestrator, "submit_planner_output", record_submit)

    result = CortexTaskSubmitter(planner).plan_and_submit(
        orchestrator,
        observation(),
        {},
        task_id="task-targeted",
        grounding_result=grounding,
        planner_output_id="planner-output-2",
        planner_trace_id="planner-trace-2",
    )

    assert captured["output"] is output
    assert captured["grounding_result"] is grounding
    assert captured["task_id"] == "task-targeted"
    assert captured["planner_output_id"] == "planner-output-2"
    assert captured["planner_trace_id"] == "planner-trace-2"
    assert result.scheduled_task.task_spec.target is grounding.target
    assert orchestrator.scheduler.current_task is None


def test_manager_rejects_unavailable_skill_from_misbehaving_planner() -> None:
    planner = RecordingPlanner(planner_output(selected_skill="basic_reach_target"))
    orchestrator = ManagerOrchestrator(
        runtime_capabilities=SkillCapabilityContract(available_skills=("continue_dialogue",))
    )

    with pytest.raises(TaskManagerError, match="not available.*basic_reach_target"):
        CortexTaskSubmitter(planner).plan_and_submit(
            orchestrator,
            observation(),
            {},
            task_id="task-1",
        )

    assert planner.calls[0][2] == ("continue_dialogue",)
    assert orchestrator.scheduler.queued_tasks == ()
    assert orchestrator.scheduler.current_task is None


@pytest.mark.parametrize(
    "grounding_result",
    [
        None,
        GroundingResult(
            status="grounding_failed",
            failure_reason="no_visible_candidate",
            evidence_ids=("shot-1",),
        ),
    ],
)
def test_target_requiring_submission_without_successful_grounding_is_rejected(
    grounding_result: GroundingResult | None,
) -> None:
    orchestrator = ManagerOrchestrator()

    with pytest.raises(ManagerGroundingError):
        CortexTaskSubmitter(
            RecordingPlanner(planner_output(selected_skill="basic_reach_target"))
        ).plan_and_submit(
            orchestrator,
            observation(),
            {},
            task_id="task-1",
            grounding_result=grounding_result,
        )

    assert orchestrator.scheduler.queued_tasks == ()
    assert orchestrator.scheduler.current_task is None


def test_fabricated_cortex_evidence_rejects_before_manager_submission() -> None:
    payload = planner_output(evidence_ids=["fabricated-shot"]).model_dump(mode="json")
    cortex = Cortex(FakeLLMClient(responses=[json.dumps(payload)]))
    orchestrator = ManagerOrchestrator()

    with pytest.raises(PlannerOutputError, match="fabricated-shot"):
        CortexTaskSubmitter(cortex).plan_and_submit(
            orchestrator,
            observation(),
            {},
            task_id="task-1",
        )

    assert orchestrator.scheduler.queued_tasks == ()
    assert orchestrator.scheduler.current_task is None


def test_direct_control_cortex_output_rejects_before_manager_submission() -> None:
    payload = planner_output().model_dump(mode="json")
    payload["key_sequence"] = ["confirm"]
    cortex = Cortex(FakeLLMClient(responses=[json.dumps(payload)]))
    orchestrator = ManagerOrchestrator()

    with pytest.raises(ValueError, match="direct primitive controls"):
        CortexTaskSubmitter(cortex).plan_and_submit(
            orchestrator,
            observation(),
            {},
            task_id="task-1",
        )

    assert orchestrator.scheduler.queued_tasks == ()


def test_synchronized_bridge_observation_reaches_pending_manager_task(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    payload_source = EvidenceRecordingBridgePayloadSource(
        EventLogger(event_log_path, run_id="run-1"),
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "Visible dialogue.",
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
    cortex = Cortex(FakeLLMClient(responses=[json.dumps(planner_output().model_dump(mode="json"))]))
    orchestrator = ManagerOrchestrator()

    result = CortexTaskSubmitter(cortex).plan_and_submit(
        orchestrator,
        bridge_observation,
        {},
        task_id="task-bridge-1",
    )

    assert payload_source.next_payload_calls == 1
    assert bridge_observation.evidence_ids == ["shot-1"]
    assert len(cortex.llm_client.requests) == 1
    assert result.planner_output.current_belief_state[0].evidence_ids == ["shot-1"]
    assert result.scheduled_task.status is TaskStatus.PENDING
    assert result.scheduled_task.task_spec.selected_skill == "continue_dialogue"
    assert result.scheduled_task.task_spec.target is None
    assert "shot-1" in result.scheduled_task.task_spec.source_evidence_ids
    assert orchestrator.scheduler.current_task is None
    assert orchestrator.scheduler.queued_tasks == (result.scheduled_task,)


def test_submission_module_has_no_execution_or_runtime_dependencies() -> None:
    source = Path(cortex_submission_module.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "ManagerTaskExecutor",
        "SkillRunner",
        "InputExecutor",
        "VerifierCatalog",
        "PrimitiveAction",
        "BoundedObservationGroundingService",
        "GroundingRequest",
        "BridgeObservationSource",
        "EventLogger",
        "MemoryDB",
        ".observe(",
        "start_next(",
    ):
        assert forbidden not in source
