from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from fh_agent.game.input_executor import InputExecutor
from fh_agent.manager.reward_profiles import RewardProfile
from fh_agent.manager.skill_contracts import SkillContract, SkillStep, merged_evidence_ids
from fh_agent.manager.verified_reward import (
    VerifiedRewardBreakdown,
    derive_verified_reward,
)
from fh_agent.observation.schemas import ActionResult, Observation, SkillResult
from fh_agent.observation.source import ObservationSource, ObservationSourceExhausted
from fh_agent.verifier.ports import OutcomeVerifier
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


class SkillEventRecord(Protocol):
    """Minimal event record surface needed by SkillRunResult."""

    event_id: str
    run_id: str
    event_type: str


class RunnableSkill(Protocol):
    @property
    def contract(self) -> SkillContract:
        """Return the skill's declarative contract."""

    def can_start(self, observation: Observation) -> bool:
        """Return whether the skill preconditions are satisfied."""

    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        """Return the next declarative primitive action decision."""


@dataclass(frozen=True, slots=True)
class SkillRunResult:
    """Complete offline skill run summary."""

    skill_result: SkillResult
    verifier_result: VerifierResult | None = None
    verifier_event_records: list[SkillEventRecord] = field(default_factory=list)
    verified_reward_breakdowns: list[VerifiedRewardBreakdown] = field(default_factory=list)
    reward_event_records: list[SkillEventRecord] = field(default_factory=list)
    action_execution_results: list[ActionResult] = field(default_factory=list)
    action_event_records: list[SkillEventRecord] = field(default_factory=list)
    steps: list[SkillStep] = field(default_factory=list)
    event_record: SkillEventRecord | None = None


class SkillRunner:
    """Runs a skill through guarded input against an observation source."""

    def __init__(
        self,
        *,
        event_logger: object | None = None,
        event_log_path: Path | None = None,
        run_id: str | None = None,
    ) -> None:
        if event_logger is None and event_log_path is not None:
            if run_id is None:
                msg = "run_id is required when event_log_path is provided"
                raise ValueError(msg)
            from fh_agent.memory.event_log import EventLogger

            event_logger = EventLogger(event_log_path, run_id=run_id)

        self.event_logger = event_logger

    def run(
        self,
        skill: RunnableSkill,
        observation_source: ObservationSource,
        *,
        verifier: OutcomeVerifier,
        input_executor: InputExecutor,
    ) -> SkillRunResult:
        try:
            start = observation_source.observe()
        except ObservationSourceExhausted:
            return self._finish(
                SkillResult(
                    skill_name=skill.contract.skill_name,
                    success=False,
                    failure_reason="empty_observation_sequence",
                    evidence_ids=[],
                    reward=None,
                ),
                steps=[],
                verifier_result=None,
                verifier_event_records=[],
                verified_reward_breakdowns=[],
                reward_event_records=[],
            )

        if not skill.can_start(start):
            return self._finish(
                SkillResult(
                    skill_name=skill.contract.skill_name,
                    success=False,
                    failure_reason="precondition_failed",
                    evidence_ids=start.evidence_ids,
                    reward=None,
                ),
                steps=[],
                verifier_result=None,
                verifier_event_records=[],
                verified_reward_breakdowns=[],
                reward_event_records=[],
            )

        steps: list[SkillStep] = []
        latest = start
        latest_verifier_result: VerifierResult | None = None
        verifier_event_records: list[SkillEventRecord] = []
        verified_reward_breakdowns: list[VerifiedRewardBreakdown] = []
        reward_event_records: list[SkillEventRecord] = []
        action_execution_results: list[ActionResult] = []
        action_event_records: list[SkillEventRecord] = []
        max_steps = skill.contract.max_steps

        for step_index in range(max_steps):
            before = latest
            step = skill.next_action(before, step_index=step_index)
            steps.append(step)

            if step.action not in skill.contract.allowed_actions:
                return self._finish(
                    self._legacy_result(
                        skill,
                        start,
                        latest,
                        success=False,
                        failure_reason="action_not_allowed",
                    ),
                    steps=steps,
                    verifier_result=latest_verifier_result,
                    verifier_event_records=verifier_event_records,
                    verified_reward_breakdowns=verified_reward_breakdowns,
                    reward_event_records=reward_event_records,
                    action_execution_results=action_execution_results,
                    action_event_records=action_event_records,
                )

            execution_result = input_executor.execute(step.action)
            if not execution_result.executed:
                linked_action_result = execution_result.model_copy(
                    update={"evidence_ids": list(before.evidence_ids)}
                )
                action_execution_results.append(linked_action_result)
                self._append_action_event(
                    action_event_records,
                    linked_action_result,
                    skill_name=skill.contract.skill_name,
                    step_index=step_index,
                    before=before,
                    after=None,
                )
                return self._finish(
                    self._legacy_result(
                        skill,
                        start,
                        latest,
                        success=False,
                        failure_reason=execution_result.blocked_reason or "input_blocked",
                    ),
                    steps=steps,
                    verifier_result=latest_verifier_result,
                    verifier_event_records=verifier_event_records,
                    verified_reward_breakdowns=verified_reward_breakdowns,
                    reward_event_records=reward_event_records,
                    action_execution_results=action_execution_results,
                    action_event_records=action_event_records,
                )

            try:
                source_after = observation_source.observe()
            except ObservationSourceExhausted:
                linked_action_result = execution_result.model_copy(
                    update={"evidence_ids": list(before.evidence_ids)}
                )
                action_execution_results.append(linked_action_result)
                self._append_action_event(
                    action_event_records,
                    linked_action_result,
                    skill_name=skill.contract.skill_name,
                    step_index=step_index,
                    before=before,
                    after=None,
                )
                return self._finish(
                    self._legacy_result(
                        skill,
                        start,
                        latest,
                        success=False,
                        failure_reason="observation_sequence_exhausted",
                    ),
                    steps=steps,
                    verifier_result=latest_verifier_result,
                    verifier_event_records=verifier_event_records,
                    verified_reward_breakdowns=verified_reward_breakdowns,
                    reward_event_records=reward_event_records,
                    action_execution_results=action_execution_results,
                    action_event_records=action_event_records,
                )

            linked_action_result = execution_result.model_copy(
                update={"evidence_ids": merged_evidence_ids(before, source_after)}
            )
            action_execution_results.append(linked_action_result)
            latest = source_after.model_copy(update={"last_action_result": linked_action_result})
            self._append_action_event(
                action_event_records,
                linked_action_result,
                skill_name=skill.contract.skill_name,
                step_index=step_index,
                before=before,
                after=source_after,
            )

            (
                latest_verifier_result,
                verifier_event_record,
                verified_reward_breakdown,
                reward_event_record,
            ) = self._verify(
                verifier,
                start,
                latest,
                skill_name=skill.contract.skill_name,
                reward_profile=skill.contract.reward_profile,
                steps_taken=len(steps),
            )
            if verifier_event_record is not None:
                verifier_event_records.append(verifier_event_record)
            verified_reward_breakdowns.append(verified_reward_breakdown)
            if reward_event_record is not None:
                reward_event_records.append(reward_event_record)
            terminal_result = self._terminal_result(
                skill,
                start,
                latest,
                latest_verifier_result,
            )
            if terminal_result is not None:
                return self._finish(
                    terminal_result,
                    steps=steps,
                    verifier_result=latest_verifier_result,
                    verifier_event_records=verifier_event_records,
                    verified_reward_breakdowns=verified_reward_breakdowns,
                    reward_event_records=reward_event_records,
                    action_execution_results=action_execution_results,
                    action_event_records=action_event_records,
                )

        return self._finish(
            self._legacy_result(
                skill,
                start,
                latest,
                success=False,
                failure_reason="timeout",
            ),
            steps=steps,
            verifier_result=latest_verifier_result,
            verifier_event_records=verifier_event_records,
            verified_reward_breakdowns=verified_reward_breakdowns,
            reward_event_records=reward_event_records,
            action_execution_results=action_execution_results,
            action_event_records=action_event_records,
        )

    def _append_action_event(
        self,
        action_event_records: list[SkillEventRecord],
        result: ActionResult,
        *,
        skill_name: str,
        step_index: int,
        before: Observation,
        after: Observation | None,
    ) -> None:
        if self.event_logger is None:
            return

        action_event_records.append(
            self.event_logger.append_action_result(
                result,
                skill_name=skill_name,
                step_index=step_index,
                before_observation_id=before.observation_id,
                after_observation_id=None if after is None else after.observation_id,
                before_evidence_ids=before.evidence_ids,
                after_evidence_ids=() if after is None else after.evidence_ids,
            )
        )

    def _verify(
        self,
        verifier: OutcomeVerifier,
        before: Observation,
        after: Observation,
        *,
        skill_name: str,
        reward_profile: RewardProfile,
        steps_taken: int,
    ) -> tuple[
        VerifierResult,
        SkillEventRecord | None,
        VerifiedRewardBreakdown,
        SkillEventRecord | None,
    ]:
        """Evaluate, derive, and durably record one canonical outcome."""
        result = verifier.verify(before, after)
        verifier_event_record = None
        reward_event_record = None
        if self.event_logger is not None:
            verifier_event_record = self.event_logger.append_verifier_result(
                result,
                skill_name=skill_name,
                steps_taken=steps_taken,
                before_observation_id=before.observation_id,
                after_observation_id=after.observation_id,
            )
        reward = derive_verified_reward(reward_profile, result)
        if verifier_event_record is not None:
            reward_event_record = self.event_logger.append_verified_reward(
                reward,
                skill_name=skill_name,
                verifier_event_id=verifier_event_record.event_id,
            )
        return result, verifier_event_record, reward, reward_event_record

    def _terminal_result(
        self,
        skill: RunnableSkill,
        before: Observation,
        after: Observation,
        verifier_result: VerifierResult,
    ) -> SkillResult | None:
        if verifier_result.status is VerifierStatus.SUCCESS:
            return self._legacy_result(
                skill,
                before,
                after,
                success=True,
                verifier_result=verifier_result,
            )
        if verifier_result.status is VerifierStatus.FAILURE:
            return self._legacy_result(
                skill,
                before,
                after,
                success=False,
                failure_reason=self._failure_reason(verifier_result),
                verifier_result=verifier_result,
            )
        if self._combat_is_legacy_failure(skill, after):
            return self._legacy_result(
                skill,
                before,
                after,
                success=False,
                failure_reason="combat_started",
            )
        return None

    @staticmethod
    def _combat_is_legacy_failure(skill: RunnableSkill, observation: Observation) -> bool:
        return "combat_started" in skill.contract.failure_detector and (
            observation.ui_state == "combat" or observation.combat_ui_visible is True
        )

    @staticmethod
    def _failure_reason(verifier_result: VerifierResult) -> str:
        if verifier_result.failure_kind is FailureKind.DEATH:
            return "death_screen"
        return verifier_result.failure_kind.value

    @staticmethod
    def _legacy_result(
        skill: RunnableSkill,
        before: Observation,
        after: Observation,
        *,
        success: bool,
        failure_reason: str | None = None,
        verifier_result: VerifierResult | None = None,
    ) -> SkillResult:
        evidence_ids = (
            verifier_result.evidence_ids
            if verifier_result is not None
            and verifier_result.status in {VerifierStatus.SUCCESS, VerifierStatus.FAILURE}
            else merged_evidence_ids(before, after)
        )
        return SkillResult(
            skill_name=skill.contract.skill_name,
            success=success,
            failure_reason=failure_reason,
            evidence_ids=evidence_ids,
            reward=None,
        )

    def _finish(
        self,
        result: SkillResult,
        *,
        steps: list[SkillStep],
        verifier_result: VerifierResult | None,
        verifier_event_records: list[SkillEventRecord],
        verified_reward_breakdowns: list[VerifiedRewardBreakdown],
        reward_event_records: list[SkillEventRecord],
        action_execution_results: list[ActionResult] | None = None,
        action_event_records: list[SkillEventRecord] | None = None,
    ) -> SkillRunResult:
        event_record = None
        if self.event_logger is not None:
            event_record = self.event_logger.append_skill_result(result)
        return SkillRunResult(
            skill_result=result,
            verifier_result=verifier_result,
            verifier_event_records=verifier_event_records,
            verified_reward_breakdowns=verified_reward_breakdowns,
            reward_event_records=reward_event_records,
            action_execution_results=(
                [] if action_execution_results is None else action_execution_results
            ),
            action_event_records=[] if action_event_records is None else action_event_records,
            steps=steps,
            event_record=event_record,
        )
