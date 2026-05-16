"""Reusable body skills that emit primitive actions only."""

from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.body.skills.interact_visible import InteractionTarget, InteractVisibleObjectSkill

__all__ = ["ContinueDialogueSkill", "InteractVisibleObjectSkill", "InteractionTarget"]
