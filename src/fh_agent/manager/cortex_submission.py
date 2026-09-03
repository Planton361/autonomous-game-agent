"""Submit one Cortex plan through the existing Manager validation boundary."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import ScheduledTask
from fh_agent.manager.target_ref import GroundingResult
from fh_agent.observation.schemas import Observation
from fh_agent.planner.planner_output import PlannerOutput
from fh_agent.skill_capabilities import UniversalSkillName


class CortexPlanner(Protocol):
    """Structural planning boundary used by Manager submission glue."""

    def plan_next_goal(
        self,
        observation: Observation,
        memory_summary: Mapping[str, Any],
        *,
        available_skills: Sequence[UniversalSkillName] | None = None,
    ) -> PlannerOutput:
        """Return one evidence-bounded planner proposal."""


@dataclass(frozen=True, slots=True)
class CortexTaskSubmissionResult:
    """The exact Cortex proposal and scheduled Manager task it produced."""

    planner_output: PlannerOutput
    scheduled_task: ScheduledTask


class CortexTaskSubmitter:
    """Compose planning and Manager submission without adding either authority."""

    def __init__(self, planner: CortexPlanner) -> None:
        self._planner = planner

    def plan_and_submit(
        self,
        orchestrator: ManagerOrchestrator,
        observation: Observation,
        memory_summary: Mapping[str, Any],
        *,
        task_id: str,
        grounding_result: GroundingResult | None = None,
        planner_output_id: str | None = None,
        planner_trace_id: str | None = None,
    ) -> CortexTaskSubmissionResult:
        """Plan within Manager capabilities, then submit the unchanged proposal."""

        available_skills = orchestrator.task_manager.runtime_capabilities.available_skills
        planner_output = self._planner.plan_next_goal(
            observation,
            memory_summary,
            available_skills=available_skills,
        )
        scheduled_task = orchestrator.submit_planner_output(
            planner_output,
            task_id=task_id,
            grounding_result=grounding_result,
            planner_output_id=planner_output_id,
            planner_trace_id=planner_trace_id,
        )
        return CortexTaskSubmissionResult(
            planner_output=planner_output,
            scheduled_task=scheduled_task,
        )
