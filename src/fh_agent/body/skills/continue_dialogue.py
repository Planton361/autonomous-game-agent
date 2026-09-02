from dataclasses import dataclass, field

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.manager.reward_computer import RewardComputer, RewardProfile
from fh_agent.manager.skill_contracts import (
    SkillContract,
    SkillStep,
    is_dialogue_observation,
    merged_evidence_ids,
)
from fh_agent.observation.schemas import Observation, SkillResult
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


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

    def evaluate(
        self,
        before: Observation,
        after: Observation,
        *,
        steps_taken: int,
    ) -> SkillResult:
        verifier_result = ContinueDialogueVerifier().verify(before, after)
        timed_out = steps_taken >= self.max_steps
        success = verifier_result.status is VerifierStatus.SUCCESS
        failure_reason: str | None = None
        if (
            verifier_result.status is VerifierStatus.FAILURE
            and verifier_result.failure_kind is FailureKind.DEATH
        ):
            failure_reason = "death_screen"
        elif not success and timed_out:
            failure_reason = "timeout"

        evidence_ids = outcome_evidence_ids(before, after, verifier_result)

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


def outcome_evidence_ids(
    before: Observation,
    after: Observation,
    verifier_result: VerifierResult,
) -> list[str]:
    """Use canonical terminal evidence, otherwise preserve legacy audit context."""

    if verifier_result.status is not VerifierStatus.ABSTAIN:
        return list(verifier_result.evidence_ids)
    return merged_evidence_ids(before, after)
