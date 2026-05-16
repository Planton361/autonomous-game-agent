from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.manager.task_spec import TaskSpec


class TaskStatus(StrEnum):
    """Lifecycle state for a scheduled TaskSpec."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset(
    {
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.TIMED_OUT,
        TaskStatus.CANCELLED,
    }
)


class TaskCompletion(BaseModel):
    """Deterministic record of why a scheduled task ended."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    task_spec: TaskSpec
    status: TaskStatus
    condition: str
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str | None = None
    elapsed_steps: int = Field(ge=0)

    @field_validator("status")
    @classmethod
    def status_must_be_terminal(cls, status: TaskStatus) -> TaskStatus:
        if status not in TERMINAL_STATUSES:
            msg = "completion status must be terminal"
            raise ValueError(msg)
        return status


class ScheduledTask(BaseModel):
    """A TaskSpec plus scheduler-local lifecycle state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_spec: TaskSpec
    status: TaskStatus = TaskStatus.PENDING
    elapsed_steps: int = Field(default=0, ge=0)
    completion: TaskCompletion | None = None


class SchedulerState(BaseModel):
    """Serializable snapshot of scheduler queues."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    current_task: ScheduledTask | None = None
    queued_tasks: tuple[ScheduledTask, ...] = ()
    completed_tasks: tuple[ScheduledTask, ...] = ()


class TaskSchedulerError(ValueError):
    """Raised when a scheduler operation violates lifecycle rules."""


class TaskScheduler:
    """In-memory FIFO scheduler for TaskSpec lifecycle state only."""

    def __init__(self) -> None:
        self._queue: list[ScheduledTask] = []
        self._current_task: ScheduledTask | None = None
        self._completed_tasks: list[ScheduledTask] = []

    @property
    def current_task(self) -> ScheduledTask | None:
        return self._current_task

    @property
    def queued_tasks(self) -> tuple[ScheduledTask, ...]:
        return tuple(self._queue)

    @property
    def completed_tasks(self) -> tuple[ScheduledTask, ...]:
        return tuple(self._completed_tasks)

    def state(self) -> SchedulerState:
        return SchedulerState(
            current_task=self._current_task,
            queued_tasks=tuple(self._queue),
            completed_tasks=tuple(self._completed_tasks),
        )

    def enqueue(self, task_spec: TaskSpec) -> ScheduledTask:
        scheduled = ScheduledTask(task_spec=task_spec, status=TaskStatus.PENDING)
        self._queue.append(scheduled)
        return scheduled

    def start_next(self) -> ScheduledTask | None:
        if self._current_task is not None or not self._queue:
            return None

        next_task = self._queue.pop(0).model_copy(update={"status": TaskStatus.RUNNING})
        self._current_task = next_task
        return next_task

    def tick(self) -> ScheduledTask | None:
        if self._current_task is None:
            return None

        elapsed_steps = self._current_task.elapsed_steps + 1
        running_task = self._current_task.model_copy(update={"elapsed_steps": elapsed_steps})
        self._current_task = running_task

        if elapsed_steps >= running_task.task_spec.timeout_steps:
            completion = self._complete_current(
                status=TaskStatus.TIMED_OUT,
                condition="timeout",
                evidence_ids=[],
                reason="timeout",
            )
            return self._completed_tasks[-1].model_copy(update={"completion": completion})

        return running_task

    def mark_success(
        self,
        condition: str,
        evidence_ids: list[str] | None = None,
    ) -> TaskCompletion:
        current = self._require_current_task()
        self._validate_condition(
            condition,
            allowed_conditions=current.task_spec.success_conditions,
            condition_kind="success",
        )
        return self._complete_current(
            status=TaskStatus.SUCCEEDED,
            condition=condition,
            evidence_ids=evidence_ids or [],
            reason=None,
        )

    def mark_failure(
        self,
        condition: str,
        evidence_ids: list[str] | None = None,
        reason: str | None = None,
    ) -> TaskCompletion:
        current = self._require_current_task()
        self._validate_condition(
            condition,
            allowed_conditions=current.task_spec.failure_conditions,
            condition_kind="failure",
        )
        return self._complete_current(
            status=TaskStatus.FAILED,
            condition=condition,
            evidence_ids=evidence_ids or [],
            reason=reason,
        )

    def cancel_current(self, reason: str) -> TaskCompletion:
        if not reason:
            msg = "cancel reason must not be empty"
            raise TaskSchedulerError(msg)

        self._require_current_task()
        return self._complete_current(
            status=TaskStatus.CANCELLED,
            condition="cancelled",
            evidence_ids=[],
            reason=reason,
        )

    def _require_current_task(self) -> ScheduledTask:
        if self._current_task is None:
            msg = "no running task"
            raise TaskSchedulerError(msg)
        return self._current_task

    def _validate_condition(
        self,
        condition: str,
        *,
        allowed_conditions: list[str],
        condition_kind: str,
    ) -> None:
        if not condition:
            msg = f"{condition_kind} condition must not be empty"
            raise TaskSchedulerError(msg)
        if allowed_conditions and condition not in allowed_conditions:
            msg = f"invalid {condition_kind} condition: {condition}"
            raise TaskSchedulerError(msg)

    def _complete_current(
        self,
        *,
        status: TaskStatus,
        condition: str,
        evidence_ids: list[str],
        reason: str | None,
    ) -> TaskCompletion:
        current = self._require_current_task()
        completion = TaskCompletion(
            task_id=current.task_spec.task_id,
            task_spec=current.task_spec,
            status=status,
            condition=condition,
            evidence_ids=evidence_ids,
            reason=reason,
            elapsed_steps=current.elapsed_steps,
        )
        completed_task = current.model_copy(
            update={
                "status": status,
                "completion": completion,
            }
        )
        self._completed_tasks.append(completed_task)
        self._current_task = None
        return completion
