from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from fh_agent.manager.reward_computer import RewardComputer
from fh_agent.manager.skill_contracts import SkillContract, SkillStep, merged_evidence_ids
from fh_agent.observation.schemas import Observation, SkillResult
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
    steps: list[SkillStep] = field(default_factory=list)
    event_record: SkillEventRecord | None = None


class SkillRunner:
    """Runs a skill against mock observations without executing inputs."""

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
        observations: Sequence[Observation],
        *,
        verifier: OutcomeVerifier,
    ) -> SkillRunResult:
        if not observations:
            return self._finish(
                SkillResult(
                    skill_name=skill.contract.skill_name,
                    success=False,
                    failure_reason="empty_observation_sequence",
                    evidence_ids=[],
                ),
                steps=[],
                verifier_result=None,
            )

        start = observations[0]
        if not skill.can_start(start):
            return self._finish(
                SkillResult(
                    skill_name=skill.contract.skill_name,
                    success=False,
                    failure_reason="precondition_failed",
                    evidence_ids=start.evidence_ids,
                ),
                steps=[],
                verifier_result=None,
            )

        steps: list[SkillStep] = []
        latest = start
        latest_verifier_result: VerifierResult | None = None
        max_steps = skill.contract.max_steps

        for step_index in range(max_steps):
            step = skill.next_action(latest, step_index=step_index)
            steps.append(step)

            next_index = step_index + 1
            if next_index >= len(observations):
                latest_verifier_result = verifier.verify(start, latest)
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
                    )

                return self._finish(
                    self._legacy_result(
                        skill,
                        start,
                        latest,
                        success=False,
                        failure_reason="observation_sequence_exhausted",
                        failure=False,
                    ),
                    steps=steps,
                    verifier_result=latest_verifier_result,
                )

            latest = observations[next_index]
            latest_verifier_result = verifier.verify(start, latest)
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
                )

        return self._finish(
            self._legacy_result(
                skill,
                start,
                latest,
                success=False,
                failure_reason="timeout",
                timeout=True,
            ),
            steps=steps,
            verifier_result=latest_verifier_result,
        )

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
        timeout: bool = False,
        failure: bool | None = None,
    ) -> SkillResult:
        evidence_ids = (
            verifier_result.evidence_ids
            if verifier_result is not None
            and verifier_result.status in {VerifierStatus.SUCCESS, VerifierStatus.FAILURE}
            else merged_evidence_ids(before, after)
        )
        reward = RewardComputer(skill.contract.reward_profile).compute(
            before,
            after,
            timeout=timeout,
            failure=failure_reason is not None if failure is None else failure,
        )
        return SkillResult(
            skill_name=skill.contract.skill_name,
            success=success,
            failure_reason=failure_reason,
            evidence_ids=evidence_ids,
            reward=reward.total,
        )

    def _finish(
        self,
        result: SkillResult,
        *,
        steps: list[SkillStep],
        verifier_result: VerifierResult | None,
    ) -> SkillRunResult:
        event_record = None
        if self.event_logger is not None:
            event_record = self.event_logger.append_skill_result(result)
        return SkillRunResult(
            skill_result=result,
            verifier_result=verifier_result,
            steps=steps,
            event_record=event_record,
        )
