from fh_agent.manager.event_sink import ManagerEventSink
from fh_agent.manager.scheduler import ScheduledTask, TaskScheduler, TaskSchedulerError
from fh_agent.manager.skill_runner import SkillRunResult
from fh_agent.manager.target_ref import GroundingResult
from fh_agent.manager.task_events import TaskCompletionEvent, task_completion_to_event
from fh_agent.manager.task_manager import TaskManager
from fh_agent.planner.planner_output import PlannerOutput
from fh_agent.skill_capabilities import SkillCapabilityContract


class ManagerOrchestrator:
    """Pure manager pipeline over planner output, task specs, and task events."""

    def __init__(
        self,
        *,
        task_manager: TaskManager | None = None,
        runtime_capabilities: SkillCapabilityContract | None = None,
        scheduler: TaskScheduler | None = None,
        event_sink: ManagerEventSink | None = None,
    ) -> None:
        if task_manager is not None and runtime_capabilities is not None:
            msg = "pass either task_manager or runtime_capabilities, not both"
            raise ValueError(msg)
        if task_manager is not None:
            self.task_manager = task_manager
        elif runtime_capabilities is not None:
            self.task_manager = TaskManager(runtime_capabilities=runtime_capabilities)
        else:
            self.task_manager = TaskManager()
        self.scheduler = scheduler or TaskScheduler()
        self.event_sink = event_sink

    def submit_planner_output(
        self,
        planner_output: PlannerOutput,
        *,
        task_id: str,
        grounding_result: GroundingResult | None = None,
        planner_output_id: str | None = None,
        planner_trace_id: str | None = None,
    ) -> ScheduledTask:
        task_spec = self.task_manager.create_task_from_planner_output(
            planner_output,
            grounding_result=grounding_result,
            planner_output_id=planner_output_id,
            planner_trace_id=planner_trace_id,
        )
        task_spec = task_spec.model_copy(update={"task_id": task_id})
        return self.scheduler.enqueue(task_spec)

    def start_next(self) -> ScheduledTask | None:
        return self.scheduler.start_next()

    def tick(
        self,
        *,
        run_id: str,
        event_id: str,
        created_at: str | None = None,
    ) -> TaskCompletionEvent | None:
        scheduled_task = self.scheduler.tick()
        if scheduled_task is None or scheduled_task.completion is None:
            return None
        event = task_completion_to_event(
            scheduled_task.completion,
            run_id=run_id,
            event_id=event_id,
            created_at=created_at,
        )
        self._record_task_completion(event)
        return event

    def mark_success(
        self,
        *,
        run_id: str,
        event_id: str,
        condition: str,
        evidence_ids: list[str] | None = None,
        created_at: str | None = None,
    ) -> TaskCompletionEvent:
        completion = self.scheduler.mark_success(condition, evidence_ids=evidence_ids)
        event = task_completion_to_event(
            completion,
            run_id=run_id,
            event_id=event_id,
            created_at=created_at,
        )
        self._record_task_completion(event)
        return event

    def mark_failure(
        self,
        *,
        run_id: str,
        event_id: str,
        condition: str,
        evidence_ids: list[str] | None = None,
        reason: str | None = None,
        created_at: str | None = None,
    ) -> TaskCompletionEvent:
        completion = self.scheduler.mark_failure(
            condition,
            evidence_ids=evidence_ids,
            reason=reason,
        )
        event = task_completion_to_event(
            completion,
            run_id=run_id,
            event_id=event_id,
            created_at=created_at,
        )
        self._record_task_completion(event)
        return event

    def cancel_current(
        self,
        *,
        run_id: str,
        event_id: str,
        reason: str,
        evidence_ids: list[str] | None = None,
        created_at: str | None = None,
    ) -> TaskCompletionEvent:
        completion = self.scheduler.cancel_current(reason, evidence_ids=evidence_ids)
        event = task_completion_to_event(
            completion,
            run_id=run_id,
            event_id=event_id,
            created_at=created_at,
        )
        self._record_task_completion(event)
        return event

    def complete_from_skill_run(
        self,
        skill_run_result: SkillRunResult,
        *,
        task_id: str,
        run_id: str,
        event_id: str,
        created_at: str | None = None,
    ) -> TaskCompletionEvent | None:
        """Close the matching task from its current terminal authority."""
        current_task = self.scheduler.current_task
        if current_task is None:
            msg = "no running task"
            raise TaskSchedulerError(msg)
        if task_id != current_task.task_spec.task_id:
            msg = "task_id does not match the running task"
            raise TaskSchedulerError(msg)
        if skill_run_result.skill_result.skill_name != current_task.task_spec.selected_skill:
            msg = "skill name does not match the running task"
            raise TaskSchedulerError(msg)

        if skill_run_result.manager_stop_result is not None:
            manager_stop_event_id = (
                skill_run_result.manager_stop_event_record.event_id
                if skill_run_result.manager_stop_event_record is not None
                else None
            )
            completion = self.scheduler.complete_from_manager_stop(
                skill_run_result.manager_stop_result,
                manager_stop_event_id=manager_stop_event_id,
            )
        else:
            verifier_result = skill_run_result.verifier_result
            if verifier_result is None:
                return None

            verifier_event_id = (
                skill_run_result.verifier_event_records[-1].event_id
                if skill_run_result.verifier_event_records
                else None
            )
            completion = self.scheduler.complete_from_verifier(
                verifier_result,
                verifier_event_id=verifier_event_id,
            )
        if completion is None:
            return None

        event = task_completion_to_event(
            completion,
            run_id=run_id,
            event_id=event_id,
            created_at=created_at,
        )
        self._record_task_completion(event)
        return event

    def _record_task_completion(self, event: TaskCompletionEvent) -> None:
        if self.event_sink is not None:
            self.event_sink.record_task_completion(event)
