import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fh_agent.manager.reward_profiles import RewardProfile
from fh_agent.manager.target_ref import GroundedTarget
from fh_agent.planner.planner_output import (
    PRIMITIVE_ACTION_NAMES,
    UniversalSkillName,
    find_direct_control_violations,
    find_hidden_state_term_violations,
)

JsonScalar = str | int | float | bool | None
JsonObject = dict[str, JsonScalar]


class TaskSpec(BaseModel):
    """Executable contract for a future Body skill without executing it."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    selected_skill: UniversalSkillName
    goal: str
    target: GroundedTarget | None = None
    constraints: JsonObject = Field(default_factory=dict)
    success_conditions: list[str] = Field(default_factory=list)
    failure_conditions: list[str] = Field(default_factory=list)
    timeout_steps: int = Field(gt=0)
    reward_profile: RewardProfile
    source_evidence_ids: list[str] = Field(default_factory=list)
    planner_output_id: str | None = None
    planner_trace_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_unsafe_task_content(cls, data: Any) -> Any:
        control_violations = find_direct_control_violations(data)
        if control_violations:
            joined = ", ".join(control_violations)
            msg = f"task spec must not contain direct primitive controls: {joined}"
            raise ValueError(msg)

        hidden_state_violations = find_hidden_state_term_violations(data)
        if hidden_state_violations:
            joined = ", ".join(hidden_state_violations)
            msg = f"task spec must not contain hidden-state terms: {joined}"
            raise ValueError(msg)

        return data

    @field_validator("selected_skill", mode="before")
    @classmethod
    def reject_primitive_selected_skill(cls, selected_skill: object) -> object:
        if isinstance(selected_skill, str) and selected_skill in PRIMITIVE_ACTION_NAMES:
            msg = (
                f"selected_skill must be a universal skill, not primitive action: {selected_skill}"
            )
            raise ValueError(msg)
        return selected_skill

    @field_validator("success_conditions", "failure_conditions")
    @classmethod
    def conditions_must_not_be_empty_strings(cls, conditions: list[str]) -> list[str]:
        if any(not condition for condition in conditions):
            msg = "conditions must not contain empty strings"
            raise ValueError(msg)
        return conditions

    def to_deterministic_json(self) -> str:
        """Serialize with sorted keys for stable logs, hashes, and tests."""

        payload = self.model_dump(exclude_none=True, mode="json", round_trip=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
