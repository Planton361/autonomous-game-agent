from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RewardTermName = Literal[
    "new_visible_text",
    "screen_transition",
    "skill_success",
    "avoid_death",
    "avoid_combat",
    "avoid_timeout",
    "avoid_repeated_no_progress",
    "information_gain",
    "hypothesis_tested",
]

ALLOWED_REWARD_TERMS: frozenset[str] = frozenset(
    {
        "new_visible_text",
        "screen_transition",
        "skill_success",
        "avoid_death",
        "avoid_combat",
        "avoid_timeout",
        "avoid_repeated_no_progress",
        "information_gain",
        "hypothesis_tested",
    }
)


class RewardTerm(BaseModel):
    """One generic reward weight for a future Body skill run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: RewardTermName
    weight: float


class RewardProfile(BaseModel):
    """Serializable generic reward contract for a TaskSpec."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_name: str
    terms: tuple[RewardTerm, ...] = Field(min_length=1)

    @field_validator("terms")
    @classmethod
    def term_names_must_be_unique(cls, terms: tuple[RewardTerm, ...]) -> tuple[RewardTerm, ...]:
        names = [term.name for term in terms]
        if len(names) != len(set(names)):
            msg = "reward term names must be unique within a profile"
            raise ValueError(msg)
        return terms


DEFAULT_REWARD_PROFILES: MappingProxyType[str, RewardProfile] = MappingProxyType(
    {
        "continue_dialogue": RewardProfile(
            profile_name="continue_dialogue_default",
            terms=(
                RewardTerm(name="new_visible_text", weight=1.0),
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_timeout", weight=0.5),
                RewardTerm(name="avoid_repeated_no_progress", weight=0.25),
            ),
        ),
        "reach_visible_target": RewardProfile(
            profile_name="reach_visible_target_default",
            terms=(
                RewardTerm(name="screen_transition", weight=1.0),
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_death", weight=1.0),
                RewardTerm(name="avoid_combat", weight=0.5),
                RewardTerm(name="avoid_timeout", weight=0.5),
                RewardTerm(name="avoid_repeated_no_progress", weight=0.25),
            ),
        ),
        "basic_reach_target": RewardProfile(
            profile_name="basic_reach_target_default",
            terms=(
                RewardTerm(name="screen_transition", weight=1.0),
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_timeout", weight=0.5),
                RewardTerm(name="avoid_repeated_no_progress", weight=0.25),
            ),
        ),
        "safe_reach_target": RewardProfile(
            profile_name="safe_reach_target_default",
            terms=(
                RewardTerm(name="screen_transition", weight=1.0),
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_death", weight=1.0),
                RewardTerm(name="avoid_combat", weight=0.75),
                RewardTerm(name="avoid_timeout", weight=0.5),
                RewardTerm(name="avoid_repeated_no_progress", weight=0.25),
            ),
        ),
        "retreat_from_hazard": RewardProfile(
            profile_name="retreat_from_hazard_default",
            terms=(
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_death", weight=1.0),
                RewardTerm(name="avoid_combat", weight=0.75),
                RewardTerm(name="avoid_timeout", weight=0.5),
            ),
        ),
        "wait_for_safe_gap": RewardProfile(
            profile_name="wait_for_safe_gap_default",
            terms=(
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_death", weight=1.0),
                RewardTerm(name="avoid_combat", weight=0.5),
                RewardTerm(name="avoid_timeout", weight=0.25),
                RewardTerm(name="avoid_repeated_no_progress", weight=0.25),
            ),
        ),
        "interact_visible_object": RewardProfile(
            profile_name="interact_visible_object_default",
            terms=(
                RewardTerm(name="new_visible_text", weight=1.0),
                RewardTerm(name="information_gain", weight=0.75),
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_death", weight=0.75),
                RewardTerm(name="avoid_timeout", weight=0.5),
            ),
        ),
        "interact_visible": RewardProfile(
            profile_name="interact_visible_default",
            terms=(
                RewardTerm(name="new_visible_text", weight=1.0),
                RewardTerm(name="information_gain", weight=0.75),
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_death", weight=0.75),
                RewardTerm(name="avoid_timeout", weight=0.5),
            ),
        ),
        "select_visible_menu_entry": RewardProfile(
            profile_name="select_visible_menu_entry_default",
            terms=(
                RewardTerm(name="new_visible_text", weight=0.75),
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="avoid_timeout", weight=0.5),
                RewardTerm(name="avoid_repeated_no_progress", weight=0.25),
            ),
        ),
    }
)


def default_reward_profile_for_skill(skill_name: str) -> RewardProfile:
    """Return the generic default reward profile for a universal skill."""

    try:
        return DEFAULT_REWARD_PROFILES[skill_name]
    except KeyError as exc:
        msg = f"no default reward profile for skill: {skill_name}"
        raise ValueError(msg) from exc
