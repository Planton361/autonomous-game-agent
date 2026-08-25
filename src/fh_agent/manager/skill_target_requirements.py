"""Neutral skill-to-visible-target requirements shared by Manager contracts."""

from types import MappingProxyType
from typing import Literal

from fh_agent.manager.target_ref import TargetType
from fh_agent.skill_capabilities import UniversalSkillName

TargetRequirement = TargetType | Literal["targetless"]

SKILL_TARGET_REQUIREMENTS: MappingProxyType[UniversalSkillName, TargetRequirement] = (
    MappingProxyType(
        {
            "continue_dialogue": "targetless",
            "basic_reach_target": "visible_screen_point",
            "interact_visible_object": "visible_object",
        }
    )
)


def target_requirement_for_skill(skill_name: UniversalSkillName) -> TargetRequirement | None:
    """Return the visible target contract for a known universal skill, if implemented."""

    return SKILL_TARGET_REQUIREMENTS.get(skill_name)
