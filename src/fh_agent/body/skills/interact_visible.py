from dataclasses import dataclass, field

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.manager.reward_computer import RewardProfile
from fh_agent.manager.skill_contracts import SkillContract, SkillStep
from fh_agent.manager.target_ref import VisibleObjectTarget
from fh_agent.observation.schemas import Observation


@dataclass(slots=True)
class InteractVisibleObjectSkill:
    """Universal interaction skill for visible or explicit mock targets."""

    target: VisibleObjectTarget | None = None
    max_steps: int = 2
    reward_profile: RewardProfile = field(default_factory=RewardProfile)

    @property
    def contract(self) -> SkillContract:
        return SkillContract(
            skill_name="interact_visible_object",
            allowed_actions=[PrimitiveAction.CONFIRM, PrimitiveAction.WAIT],
            preconditions=["interaction_target_visible"],
            success_detector=[
                "dialogue_visible",
                "interaction_outcome_visible",
            ],
            failure_detector=["death_screen", "timeout", "repeated_no_change"],
            max_steps=self.max_steps,
            reward_profile=self.reward_profile,
        )

    def can_start(self, observation: Observation) -> bool:
        return self.target is not None or has_visible_target(observation)

    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        if self.can_start(observation):
            return SkillStep(
                skill_name=self.contract.skill_name,
                action=PrimitiveAction.CONFIRM,
                step_index=step_index,
                reason="interaction_target_visible",
                evidence_ids=step_evidence_ids(observation, self.target),
            )

        return SkillStep(
            skill_name=self.contract.skill_name,
            action=PrimitiveAction.WAIT,
            step_index=step_index,
            reason="no_visible_interaction_target",
            evidence_ids=observation.evidence_ids,
        )


def has_visible_target(observation: Observation) -> bool:
    return bool(
        observation.visible_sprites
        or observation.visible_sprite_screen_positions
        or observation.visible_sprite_visual_hashes
    )


def step_evidence_ids(
    observation: Observation,
    target: VisibleObjectTarget | None,
) -> list[str]:
    evidence_ids = list(observation.evidence_ids)
    if target is not None:
        for evidence_id in target.evidence_ids:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids
