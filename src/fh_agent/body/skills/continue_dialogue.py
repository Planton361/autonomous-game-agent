from dataclasses import dataclass, field

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.manager.reward_computer import RewardProfile
from fh_agent.manager.skill_contracts import SkillContract, SkillStep, is_dialogue_observation
from fh_agent.observation.schemas import Observation


@dataclass(slots=True)
class ContinueDialogueSkill:
    """Universal dialogue-advance skill for visible dialogue observations."""

    max_steps: int = 3
    reward_profile: RewardProfile = field(default_factory=RewardProfile)

    @property
    def contract(self) -> SkillContract:
        return SkillContract(
            skill_name="continue_dialogue",
            allowed_actions=[PrimitiveAction.CONFIRM, PrimitiveAction.WAIT],
            preconditions=["dialogue_visible"],
            success_detector=["visible_text_changed", "dialogue_closed"],
            failure_detector=["death_screen", "timeout", "repeated_no_change"],
            max_steps=self.max_steps,
            reward_profile=self.reward_profile,
        )

    def can_start(self, observation: Observation) -> bool:
        return is_dialogue_observation(observation)

    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        if self.can_start(observation):
            return SkillStep(
                skill_name=self.contract.skill_name,
                action=PrimitiveAction.CONFIRM,
                step_index=step_index,
                reason="dialogue_visible",
                evidence_ids=observation.evidence_ids,
            )

        return SkillStep(
            skill_name=self.contract.skill_name,
            action=PrimitiveAction.WAIT,
            step_index=step_index,
            reason="precondition_not_met",
            evidence_ids=observation.evidence_ids,
        )
