"""Compose one bounded Cortex-to-Manager task attempt through existing boundaries."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fh_agent.game.input_executor import InputExecutor
from fh_agent.manager.grounded_cortex_submission import (
    GroundedCortexTaskSubmissionResult,
    GroundedCortexTaskSubmitter,
)
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import ScheduledTask, TaskStatus
from fh_agent.manager.task_executor import ManagerTaskExecutor, TaskExecutionResult
from fh_agent.observation.primed_source import PrimedObservationSource
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import ObservationSource


class HierarchicalTaskStepError(ValueError):
    """Raised when a one-step composition precondition is not satisfied."""


@dataclass(frozen=True, slots=True)
class HierarchicalTaskStepResult:
    """Exact boundary records produced by one hierarchical task attempt."""

    planning_observation: Observation
    submission_result: GroundedCortexTaskSubmissionResult
    started_task: ScheduledTask
    execution_result: TaskExecutionResult


class HierarchicalTaskStepRunner:
    """Compose one plan, grounded submission, start, and bounded execution attempt."""

    def __init__(
        self,
        submitter: GroundedCortexTaskSubmitter,
        *,
        task_executor: ManagerTaskExecutor | None = None,
    ) -> None:
        self._submitter = submitter
        self._task_executor = task_executor or ManagerTaskExecutor()

    def run_once(
        self,
        orchestrator: ManagerOrchestrator,
        observation_source: ObservationSource,
        input_executor: InputExecutor,
        memory_summary: Mapping[str, Any],
        *,
        task_id: str,
        run_id: str,
        completion_event_id: str,
        planner_output_id: str | None = None,
        planner_trace_id: str | None = None,
        created_at: str | None = None,
    ) -> HierarchicalTaskStepResult:
        """Run exactly one Manager-owned hierarchical task attempt."""

        if orchestrator.scheduler.current_task is not None or orchestrator.scheduler.queued_tasks:
            msg = "hierarchical task step requires an idle Manager scheduler"
            raise HierarchicalTaskStepError(msg)

        planning_observation = observation_source.observe()
        submission_result = self._submitter.plan_ground_and_submit(
            orchestrator,
            planning_observation,
            memory_summary,
            task_id=task_id,
            planner_output_id=planner_output_id,
            planner_trace_id=planner_trace_id,
        )
        started_task = orchestrator.start_next()
        if (
            started_task is None
            or started_task.status is not TaskStatus.RUNNING
            or started_task.task_spec.task_id != submission_result.scheduled_task.task_spec.task_id
        ):
            msg = "Manager did not start the newly submitted task"
            raise HierarchicalTaskStepError(msg)

        runtime_source = PrimedObservationSource(planning_observation, observation_source)
        execution_result = self._task_executor.execute_current_task(
            orchestrator,
            runtime_source,
            input_executor,
            run_id=run_id,
            completion_event_id=completion_event_id,
            created_at=created_at,
        )
        return HierarchicalTaskStepResult(
            planning_observation=planning_observation,
            submission_result=submission_result,
            started_task=started_task,
            execution_result=execution_result,
        )
