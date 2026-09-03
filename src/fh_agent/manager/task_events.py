from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.manager.runtime_stop import ManagerStopResult
from fh_agent.manager.scheduler import TaskCompletion, TaskStatus
from fh_agent.manager.task_spec import JsonObject
from fh_agent.verifier.schemas import VerifierResult


class TaskCompletionEvent(BaseModel):
    """Persistable event payload for a completed manager task."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    run_id: str
    event_type: Literal["task_completion"] = "task_completion"
    task_id: str
    selected_skill: str
    goal: str
    target: JsonObject | None
    status: TaskStatus
    condition: str
    reason: str | None = None
    elapsed_steps: int = Field(ge=0)
    timeout_steps: int = Field(gt=0)
    planner_output_id: str | None = None
    planner_trace_id: str | None = None
    source_evidence_ids: list[str] = Field(default_factory=list)
    completion_evidence_ids: list[str] = Field(default_factory=list)
    reward_terms: list[str] = Field(default_factory=list)
    verifier_result: VerifierResult | None = None
    verifier_event_id: str | None = None
    manager_stop_result: ManagerStopResult | None = None
    manager_stop_event_id: str | None = None
    created_at: str

    @field_validator("event_id", "run_id", "task_id", "selected_skill", "goal", "condition")
    @classmethod
    def required_strings_must_not_be_empty(cls, value: str) -> str:
        if not value:
            msg = "required string fields must not be empty"
            raise ValueError(msg)
        return value

    @field_validator("verifier_event_id")
    @classmethod
    def verifier_event_id_must_not_be_empty(cls, verifier_event_id: str | None) -> str | None:
        if verifier_event_id == "":
            msg = "verifier_event_id must not be empty"
            raise ValueError(msg)
        return verifier_event_id

    @field_validator("manager_stop_event_id")
    @classmethod
    def manager_stop_event_id_must_not_be_empty(
        cls, manager_stop_event_id: str | None
    ) -> str | None:
        if manager_stop_event_id == "":
            msg = "manager_stop_event_id must not be empty"
            raise ValueError(msg)
        return manager_stop_event_id


def task_completion_to_event(
    completion: TaskCompletion,
    *,
    run_id: str,
    event_id: str,
    created_at: str | None = None,
) -> TaskCompletionEvent:
    """Convert a scheduler completion into a JSON-serializable manager event."""

    task_spec = completion.task_spec
    return TaskCompletionEvent(
        event_id=event_id,
        run_id=run_id,
        task_id=completion.task_id,
        selected_skill=str(task_spec.selected_skill),
        goal=task_spec.goal,
        target=(task_spec.target.model_dump(mode="json") if task_spec.target else None),
        status=completion.status,
        condition=completion.condition,
        reason=completion.reason,
        elapsed_steps=completion.elapsed_steps,
        timeout_steps=task_spec.timeout_steps,
        planner_output_id=task_spec.planner_output_id,
        planner_trace_id=task_spec.planner_trace_id,
        source_evidence_ids=list(task_spec.source_evidence_ids),
        completion_evidence_ids=list(completion.evidence_ids),
        reward_terms=[str(term.name) for term in task_spec.reward_profile.terms],
        verifier_result=completion.verifier_result,
        verifier_event_id=completion.verifier_event_id,
        manager_stop_result=completion.manager_stop_result,
        manager_stop_event_id=completion.manager_stop_event_id,
        created_at=created_at or datetime.now(UTC).isoformat(),
    )
