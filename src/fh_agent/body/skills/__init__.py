"""Reusable body skills that emit primitive actions only."""

from fh_agent.body.skills.basic_reach_target import BasicReachTargetSkill, ScreenTarget
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.body.skills.interact_visible import InteractionTarget, InteractVisibleObjectSkill

__all__ = [
    "BasicReachTargetSkill",
    "ContinueDialogueSkill",
    "InteractVisibleObjectSkill",
    "InteractionTarget",
    "ScreenTarget",
]
