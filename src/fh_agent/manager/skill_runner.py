from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from fh_agent.manager.skill_contracts import SkillContract, SkillStep
from fh_agent.memory.event_log import EventLogger, EventRecord
from fh_agent.observation.schemas import Observation, SkillResult


class RunnableSkill(Protocol):
    @property
    def contract(self) -> SkillContract:
        """Return the skill's declarative contract."""

    def can_start(self, observation: Observation) -> bool:
        """Return whether the skill preconditions are satisfied."""

    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        """Return the next declarative primitive action decision."""

    def evaluate(
        self,
        before: Observation,
        after: Observation,
        *,
        steps_taken: int,
    ) -> SkillResult:
        """Evaluate the skill outcome against visible observations."""


@dataclass(frozen=True, slots=True)
class SkillRunResult:
    """Complete offline skill run summary."""

    skill_result: SkillResult
    steps: list[SkillStep] = field(default_factory=list)
    event_record: EventRecord | None = None


class SkillRunner:
    """Runs a skill against mock observations without executing inputs."""

    def __init__(
        self,
        *,
        event_logger: EventLogger | None = None,
        event_log_path: Path | None = None,
        run_id: str | None = None,
    ) -> None:
        if event_logger is None and event_log_path is not None:
            if run_id is None:
                msg = "run_id is required when event_log_path is provided"
                raise ValueError(msg)
            event_logger = EventLogger(event_log_path, run_id=run_id)

        self.event_logger = event_logger

    def run(self, skill: RunnableSkill, observations: Sequence[Observation]) -> SkillRunResult:
        if not observations:
            return self._finish(
                SkillResult(
                    skill_name=skill.contract.skill_name,
                    success=False,
                    failure_reason="empty_observation_sequence",
                    evidence_ids=[],
                ),
                steps=[],
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
            )

        steps: list[SkillStep] = []
        latest = start
        max_steps = skill.contract.max_steps

        for step_index in range(max_steps):
            step = skill.next_action(latest, step_index=step_index)
            steps.append(step)

            next_index = step_index + 1
            if next_index >= len(observations):
                result = skill.evaluate(start, latest, steps_taken=len(steps))
                if result.success:
                    return self._finish(result, steps=steps)

                return self._finish(
                    result.model_copy(update={"failure_reason": "observation_sequence_exhausted"}),
                    steps=steps,
                )

            latest = observations[next_index]
            result = skill.evaluate(start, latest, steps_taken=len(steps))
            if result.success or result.failure_reason is not None:
                return self._finish(result, steps=steps)

        result = skill.evaluate(start, latest, steps_taken=len(steps))
        if result.success:
            return self._finish(result, steps=steps)

        if result.failure_reason is None:
            result = result.model_copy(update={"failure_reason": "timeout", "success": False})
        return self._finish(result, steps=steps)

    def _finish(self, result: SkillResult, *, steps: list[SkillStep]) -> SkillRunResult:
        event_record = None
        if self.event_logger is not None:
            event_record = self.event_logger.append_skill_result(result)
        return SkillRunResult(skill_result=result, steps=steps, event_record=event_record)
