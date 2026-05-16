from fh_agent.manager.event_sink import ManagerEventSink
from fh_agent.manager.scheduler import ScheduledTask, TaskScheduler
from fh_agent.manager.task_events import TaskCompletionEvent, task_completion_to_event
from fh_agent.manager.task_manager import TaskManager
from fh_agent.planner.planner_output import PlannerOutput


class ManagerOrchestrator:
    """Pure manager pipeline over planner output, task specs, and task events."""

    def __init__(
        self,
        *,
        task_manager: TaskManager | None = None,
        scheduler: TaskScheduler | None = None,
        event_sink: ManagerEventSink | None = None,
    ) -> None:
        self.task_manager = task_manager or TaskManager()
        self.scheduler = scheduler or TaskScheduler()
        self.event_sink = event_sink

    def submit_planner_output(
        self,
        planner_output: PlannerOutput,
        *,
        task_id: str,
        planner_output_id: str | None = None,
        planner_trace_id: str | None = None,
    ) -> ScheduledTask:
        task_spec = self.task_manager.create_task_from_planner_output(
            planner_output,
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

    def _record_task_completion(self, event: TaskCompletionEvent) -> None:
        if self.event_sink is not None:
            self.event_sink.record_task_completion(event)
