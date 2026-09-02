from dataclasses import dataclass, field

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.manager.reward_computer import RewardComputer, RewardProfile, observation_visible_text
from fh_agent.manager.skill_contracts import SkillContract, SkillStep, merged_evidence_ids
from fh_agent.manager.target_ref import VisibleObjectTarget
from fh_agent.observation.schemas import Observation, SkillResult


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
                "visible_text_changed",
                "screen_signature_changed",
                "new_evidence",
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

    def evaluate(
        self,
        before: Observation,
        after: Observation,
        *,
        steps_taken: int,
    ) -> SkillResult:
        evidence_ids = merged_evidence_ids(before, after)
        timed_out = steps_taken >= self.max_steps
        success = self._is_success(before, after)
        failure_reason = None
        if after.ui_state == "death" or after.death_screen_visible is True:
            success = False
            failure_reason = "death_screen"
        elif not success and timed_out:
            failure_reason = "timeout"

        reward = RewardComputer(self.reward_profile).compute(
            before,
            after,
            timeout=timed_out and not success,
            failure=failure_reason is not None,
        )

        return SkillResult(
            skill_name=self.contract.skill_name,
            success=success,
            failure_reason=failure_reason,
            reward=reward.total,
            evidence_ids=evidence_ids,
        )

    def _is_success(self, before: Observation, after: Observation) -> bool:
        ui_state_outcome = after.ui_state in {"dialogue", "menu", "combat"} and (
            after.ui_state != before.ui_state
        )
        text_changed = observation_visible_text(before) != observation_visible_text(after)
        text_appeared = not observation_visible_text(before) and bool(
            observation_visible_text(after)
        )
        signature_changed = (
            before.screen_signature is not None
            and after.screen_signature is not None
            and before.screen_signature != after.screen_signature
        )
        new_evidence = bool(set(after.evidence_ids) - set(before.evidence_ids))
        visible_action_outcome = (
            after.last_action_result is not None
            and after.last_action_result.executed
            and new_evidence
        )
        return (
            ui_state_outcome
            or text_changed
            or text_appeared
            or signature_changed
            or visible_action_outcome
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
