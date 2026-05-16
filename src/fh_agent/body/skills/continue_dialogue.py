from dataclasses import dataclass, field

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.manager.reward_computer import RewardComputer, RewardProfile, observation_visible_text
from fh_agent.manager.skill_contracts import (
    SkillContract,
    SkillStep,
    is_dialogue_observation,
    merged_evidence_ids,
)
from fh_agent.observation.schemas import Observation, SkillResult


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
            success_detector=["visible_text_changed", "dialogue_closed", "new_evidence"],
            failure_detector=["timeout", "repeated_no_change"],
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
        if not success and timed_out:
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
        text_changed = observation_visible_text(before) != observation_visible_text(after)
        dialogue_closed = is_dialogue_observation(before) and not is_dialogue_observation(after)
        new_evidence = bool(set(after.evidence_ids) - set(before.evidence_ids))
        return text_changed or dialogue_closed or new_evidence
