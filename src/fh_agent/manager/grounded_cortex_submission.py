"""Compose Cortex planning, visible grounding, and Manager task submission."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fh_agent.manager.cortex_submission import CortexPlanner
from fh_agent.manager.grounding import (
    BoundedObservationGroundingService,
    GroundingRequest,
    GroundingService,
)
from fh_agent.manager.grounding_request_builder import build_grounding_request
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import ScheduledTask
from fh_agent.manager.target_ref import GroundingResult
from fh_agent.observation.schemas import Observation
from fh_agent.planner.planner_output import PlannerOutput


@dataclass(frozen=True, slots=True)
class GroundedCortexTaskSubmissionResult:
    """The exact planning, grounding, and scheduling records for one submission."""

    planner_output: PlannerOutput
    grounding_request: GroundingRequest | None
    grounding_result: GroundingResult | None
    scheduled_task: ScheduledTask


class GroundedCortexTaskSubmitter:
    """Compose existing planning, grounding, and Manager authority boundaries."""

    def __init__(
        self,
        planner: CortexPlanner,
        *,
        grounding_service: GroundingService | None = None,
    ) -> None:
        self._planner = planner
        self._grounding_service = grounding_service or BoundedObservationGroundingService()

    def plan_ground_and_submit(
        self,
        orchestrator: ManagerOrchestrator,
        observation: Observation,
        memory_summary: Mapping[str, Any],
        *,
        task_id: str,
        planner_output_id: str | None = None,
        planner_trace_id: str | None = None,
    ) -> GroundedCortexTaskSubmissionResult:
        """Plan under Manager capabilities, ground if needed, then submit unchanged."""

        available_skills = orchestrator.task_manager.runtime_capabilities.available_skills
        planner_output = self._planner.plan_next_goal(
            observation,
            memory_summary,
            available_skills=available_skills,
        )
        grounding_request = build_grounding_request(planner_output, observation)
        grounding_result = (
            self._grounding_service.ground(grounding_request, observation)
            if grounding_request is not None
            else None
        )
        scheduled_task = orchestrator.submit_planner_output(
            planner_output,
            task_id=task_id,
            grounding_result=grounding_result,
            planner_output_id=planner_output_id,
            planner_trace_id=planner_trace_id,
        )
        return GroundedCortexTaskSubmissionResult(
            planner_output=planner_output,
            grounding_request=grounding_request,
            grounding_result=grounding_result,
            scheduled_task=scheduled_task,
        )
