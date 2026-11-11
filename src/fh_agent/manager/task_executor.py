"""Execute one already-running Manager task through existing runtime boundaries."""

from dataclasses import dataclass

from fh_agent.game.input_executor import InputExecutor
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskSchedulerError
from fh_agent.manager.skill_catalog import SkillCatalog
from fh_agent.manager.skill_runner import SkillRunner, SkillRunResult
from fh_agent.manager.task_events import TaskCompletionEvent
from fh_agent.manager.verifier_catalog import VerifierCatalog
from fh_agent.observation.source import ObservationSource


class TaskExecutionError(ValueError):
    """Raised when a task's resolved runtime binding violates its Manager contract."""


@dataclass(frozen=True, slots=True)
class TaskExecutionResult:
    """Result of one bounded attempt to execute the current Manager task."""

    task_id: str
    skill_run_result: SkillRunResult
    completion_event: TaskCompletionEvent | None


class ManagerTaskExecutor:
    """Compose existing Manager, Body, Verifier, and guarded runtime boundaries."""

    def __init__(
        self,
        *,
        skill_catalog: SkillCatalog | None = None,
        verifier_catalog: VerifierCatalog | None = None,
        skill_runner: SkillRunner | None = None,
    ) -> None:
        self._skill_catalog = skill_catalog or SkillCatalog.default()
        self._verifier_catalog = verifier_catalog or VerifierCatalog()
        self._skill_runner = skill_runner or SkillRunner()

    def execute_current_task(
        self,
        orchestrator: ManagerOrchestrator,
        observation_source: ObservationSource,
        input_executor: InputExecutor,
        *,
        run_id: str,
        completion_event_id: str,
        created_at: str | None = None,
    ) -> TaskExecutionResult:
        """Run the current task once without changing Manager execution authority."""

        current_task = orchestrator.scheduler.current_task
        if current_task is None:
            raise TaskSchedulerError("no running task")

        task_spec = current_task.task_spec
        skill = self._skill_catalog.get(task_spec.selected_skill, task=task_spec.target)
        if skill.contract.skill_name != task_spec.selected_skill:
            raise TaskExecutionError(
                "resolved skill contract does not match Manager-selected skill: "
                f"{skill.contract.skill_name} != {task_spec.selected_skill}"
            )
        verifier = self._verifier_catalog.for_task(task_spec)
        skill_run_result = self._skill_runner.run(
            skill,
            observation_source,
            verifier=verifier,
            input_executor=input_executor,
        )
        completion_event = orchestrator.complete_from_skill_run(
            skill_run_result,
            task_id=task_spec.task_id,
            run_id=run_id,
            event_id=completion_event_id,
            created_at=created_at,
        )
        return TaskExecutionResult(
            task_id=task_spec.task_id,
            skill_run_result=skill_run_result,
            completion_event=completion_event,
        )
