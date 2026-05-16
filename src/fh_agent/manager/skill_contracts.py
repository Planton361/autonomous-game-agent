from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.manager.reward_computer import RewardProfile
from fh_agent.observation.schemas import Observation

SkillCondition = Literal[
    "dialogue_visible",
    "dialogue_closed",
    "interaction_target_visible",
    "interaction_outcome_visible",
    "visible_text_changed",
    "new_evidence",
    "screen_signature_changed",
    "death_screen",
    "timeout",
    "repeated_no_change",
]


class SkillContract(BaseModel):
    """Serializable contract for a reusable body skill."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str
    allowed_actions: list[PrimitiveAction]
    preconditions: list[SkillCondition]
    success_detector: list[SkillCondition]
    failure_detector: list[SkillCondition]
    max_steps: int = Field(gt=0)
    reward_profile: RewardProfile = Field(default_factory=RewardProfile)

    @field_validator("allowed_actions")
    @classmethod
    def allowed_actions_must_not_be_empty(
        cls,
        allowed_actions: list[PrimitiveAction],
    ) -> list[PrimitiveAction]:
        if not allowed_actions:
            msg = "allowed_actions must not be empty"
            raise ValueError(msg)
        return allowed_actions


class SkillStep(BaseModel):
    """One primitive action proposed by a skill, without direct input execution."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str
    action: PrimitiveAction
    step_index: int = Field(ge=0)
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


def is_dialogue_observation(observation: Observation) -> bool:
    return (
        observation.ui_state == "dialogue"
        or observation.message_window_visible is True
        or bool(observation.visible_message_text)
        or bool(observation.visible_text_spans)
    )


def merged_evidence_ids(*observations: Observation) -> list[str]:
    evidence_ids: list[str] = []
    for observation in observations:
        for evidence_id in observation.evidence_ids:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids
