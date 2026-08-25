from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

UniversalSkillName = Literal[
    "continue_dialogue",
    "basic_reach_target",
    "interact_visible",
    "interact_visible_object",
    "safe_reach_target",
]

DEFAULT_RUNTIME_SKILLS: tuple[UniversalSkillName, ...] = (
    "basic_reach_target",
    "continue_dialogue",
    "interact_visible_object",
)


class SkillCapabilityContract(BaseModel):
    """Universal skills available to the Cortex for one planning call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    available_skills: tuple[UniversalSkillName, ...]

    @field_validator("available_skills")
    @classmethod
    def available_skills_must_be_unique(
        cls,
        available_skills: tuple[UniversalSkillName, ...],
    ) -> tuple[UniversalSkillName, ...]:
        if len(available_skills) != len(set(available_skills)):
            msg = "available skills must be unique"
            raise ValueError(msg)
        return available_skills


DEFAULT_RUNTIME_CAPABILITIES = SkillCapabilityContract(available_skills=DEFAULT_RUNTIME_SKILLS)
