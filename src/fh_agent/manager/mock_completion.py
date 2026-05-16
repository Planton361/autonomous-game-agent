from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskSchedulerError
from fh_agent.manager.task_events import TaskCompletionEvent

MockCompletionStatus = Literal["succeeded", "failed", "cancelled"]


class MockSkillCompletionSignal(BaseModel):
    """Dry-run signal that simulates a terminal skill outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    status: MockCompletionStatus
    condition: str
    reason: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("task_id", "condition")
    @classmethod
    def required_strings_must_not_be_empty(cls, value: str) -> str:
        if not value:
            msg = "required string fields must not be empty"
            raise ValueError(msg)
        return value


def apply_mock_completion_signal(
    orchestrator: ManagerOrchestrator,
    signal: MockSkillCompletionSignal,
    *,
    run_id: str,
    event_id: str,
    created_at: str | None = None,
) -> TaskCompletionEvent:
    """Apply a simulated skill completion to the current orchestrator task."""

    current_task = orchestrator.scheduler.current_task
    if current_task is None:
        msg = "no running task for mock completion signal"
        raise TaskSchedulerError(msg)
    if signal.task_id != current_task.task_spec.task_id:
        msg = f"mock completion task_id does not match current task: {signal.task_id}"
        raise TaskSchedulerError(msg)

    if signal.status == "succeeded":
        return orchestrator.mark_success(
            run_id=run_id,
            event_id=event_id,
            condition=signal.condition,
            evidence_ids=signal.evidence_ids,
            created_at=created_at,
        )
    if signal.status == "failed":
        return orchestrator.mark_failure(
            run_id=run_id,
            event_id=event_id,
            condition=signal.condition,
            evidence_ids=signal.evidence_ids,
            reason=signal.reason,
            created_at=created_at,
        )

    return orchestrator.cancel_current(
        run_id=run_id,
        event_id=event_id,
        reason=signal.reason or signal.condition,
        evidence_ids=signal.evidence_ids,
        created_at=created_at,
    )
