import hashlib
import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import ValidationError

from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.skill_target_requirements import target_requirement_for_skill
from fh_agent.manager.target_ref import (
    GroundedTarget,
    GroundingFailureReason,
    GroundingResult,
)
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.planner.planner_output import (
    PRIMITIVE_ACTION_NAMES,
    PlannerOutput,
    find_direct_control_violations,
    find_hidden_state_term_violations,
)
from fh_agent.skill_capabilities import (
    DEFAULT_RUNTIME_CAPABILITIES,
    SkillCapabilityContract,
    UniversalSkillName,
)

DEFAULT_TIMEOUT_STEPS: Mapping[str, int] = {
    "continue_dialogue": 6,
    "basic_reach_target": 60,
    "interact_visible_object": 12,
    "safe_reach_target": 90,
}

DEFAULT_FAILURE_CONDITIONS: tuple[str, ...] = (
    "death_screen",
    "timeout",
    "no_progress",
)


class TaskManagerError(ValueError):
    """Raised when a planner output cannot be converted into a safe TaskSpec."""


ManagerGroundingErrorCode = Literal[
    "missing_grounding",
    "grounding_failed",
    "unexpected_grounding",
    "incompatible_target_type",
    "unsupported_skill_target_contract",
]


class ManagerGroundingError(TaskManagerError):
    """Structured rejection at the Manager's grounding boundary."""

    def __init__(
        self,
        *,
        selected_skill: UniversalSkillName,
        error_code: ManagerGroundingErrorCode,
        failure_reason: GroundingFailureReason | None = None,
        evidence_ids: tuple[str, ...] = (),
    ) -> None:
        self.selected_skill = selected_skill
        self.error_code = error_code
        self.failure_reason = failure_reason
        self.evidence_ids = tuple(dict.fromkeys(evidence_ids))
        detail = f"manager grounding rejected {selected_skill}: {error_code}"
        if failure_reason is not None:
            detail = f"{detail} ({failure_reason})"
        super().__init__(detail)


class TaskManager:
    """Pure translator from validated planner intent to TaskSpec contracts."""

    def __init__(
        self,
        *,
        runtime_capabilities: SkillCapabilityContract = DEFAULT_RUNTIME_CAPABILITIES,
    ) -> None:
        self.runtime_capabilities = runtime_capabilities

    def create_task_from_planner_output(
        self,
        planner_output: PlannerOutput | Mapping[str, Any],
        *,
        grounding_result: GroundingResult | None = None,
        planner_output_id: str | None = None,
        planner_trace_id: str | None = None,
    ) -> TaskSpec:
        output = self._coerce_planner_output(planner_output)
        output_payload = output.model_dump(mode="json")
        self._reject_unsafe_payload(output_payload)

        selected_skill = output.selected_skill
        if selected_skill in PRIMITIVE_ACTION_NAMES:
            msg = (
                f"selected_skill must be a universal skill, not primitive action: {selected_skill}"
            )
            raise TaskManagerError(msg)
        if selected_skill not in self.runtime_capabilities.available_skills:
            msg = f"selected_skill is not available to this TaskManager: {selected_skill}"
            raise TaskManagerError(msg)

        target = self._validated_target(selected_skill, grounding_result)

        reward_profile = default_reward_profile_for_skill(selected_skill)
        timeout_steps = DEFAULT_TIMEOUT_STEPS.get(selected_skill, 60)
        task_payload = {
            "task_id": "task-pending",
            "selected_skill": selected_skill,
            "goal": output.next_goal,
            "target": target,
            "constraints": {
                "avoid_known_dangers": output.risk_limit.avoid_known_dangers,
                "max_danger_score": output.risk_limit.max_danger_score,
            },
            "success_conditions": list(output.success_condition),
            "failure_conditions": list(DEFAULT_FAILURE_CONDITIONS),
            "timeout_steps": timeout_steps,
            "reward_profile": reward_profile,
            "source_evidence_ids": self._source_evidence_ids(
                output,
                grounding_result=grounding_result,
                target=target,
            ),
            "planner_output_id": planner_output_id,
            "planner_trace_id": planner_trace_id,
        }
        logical_task = TaskSpec.model_validate(task_payload)
        return logical_task.model_copy(
            update={"task_id": self._task_id_for_task_spec(logical_task)}
        )

    def _validated_target(
        self,
        selected_skill: UniversalSkillName,
        grounding_result: GroundingResult | None,
    ) -> GroundedTarget | None:
        requirement = target_requirement_for_skill(selected_skill)
        if requirement is None:
            raise ManagerGroundingError(
                selected_skill=selected_skill,
                error_code="unsupported_skill_target_contract",
            )

        if requirement == "targetless":
            if grounding_result is not None:
                raise ManagerGroundingError(
                    selected_skill=selected_skill,
                    error_code="unexpected_grounding",
                    failure_reason=grounding_result.failure_reason,
                    evidence_ids=self._grounding_evidence_ids(grounding_result),
                )
            return None

        if grounding_result is None:
            raise ManagerGroundingError(
                selected_skill=selected_skill,
                error_code="missing_grounding",
            )
        if grounding_result.status == "grounding_failed":
            raise ManagerGroundingError(
                selected_skill=selected_skill,
                error_code="grounding_failed",
                failure_reason=grounding_result.failure_reason,
                evidence_ids=grounding_result.evidence_ids,
            )

        target = grounding_result.target
        if target is None:  # GroundingResult enforces this; retain a defensive boundary.
            raise ManagerGroundingError(
                selected_skill=selected_skill,
                error_code="missing_grounding",
                evidence_ids=grounding_result.evidence_ids,
            )
        if target.target_type != requirement:
            raise ManagerGroundingError(
                selected_skill=selected_skill,
                error_code="incompatible_target_type",
                evidence_ids=self._grounding_evidence_ids(grounding_result),
            )
        return target

    def _coerce_planner_output(
        self,
        planner_output: PlannerOutput | Mapping[str, Any],
    ) -> PlannerOutput:
        if isinstance(planner_output, PlannerOutput):
            return planner_output
        if isinstance(planner_output, Mapping):
            self._reject_unsafe_payload(planner_output)
            try:
                return PlannerOutput.model_validate(planner_output)
            except ValidationError as exc:
                msg = "invalid planner output"
                raise TaskManagerError(msg) from exc

        msg = "planner_output must be a PlannerOutput or mapping"
        raise TaskManagerError(msg)

    def _reject_unsafe_payload(self, payload: Any) -> None:
        control_violations = find_direct_control_violations(payload)
        if control_violations:
            joined = ", ".join(control_violations)
            msg = f"planner output must not contain direct primitive controls: {joined}"
            raise TaskManagerError(msg)

        hidden_state_violations = find_hidden_state_term_violations(payload)
        if hidden_state_violations:
            joined = ", ".join(hidden_state_violations)
            msg = f"planner output must not contain hidden-state terms: {joined}"
            raise TaskManagerError(msg)

    def _source_evidence_ids(
        self,
        planner_output: PlannerOutput,
        *,
        grounding_result: GroundingResult | None,
        target: GroundedTarget | None,
    ) -> list[str]:
        evidence_ids: list[str] = []
        for claim in planner_output.current_belief_state:
            for evidence_id in claim.evidence_ids:
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
        for update in planner_output.memory_updates_requested:
            for evidence_id in update.evidence_ids:
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
        if target is not None:
            for evidence_id in target.evidence_ids:
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
        if grounding_result is not None:
            for evidence_id in grounding_result.evidence_ids:
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
        return evidence_ids

    def _grounding_evidence_ids(self, grounding_result: GroundingResult) -> tuple[str, ...]:
        evidence_ids = list(grounding_result.evidence_ids)
        if grounding_result.target is not None:
            evidence_ids.extend(grounding_result.target.evidence_ids)
        return tuple(dict.fromkeys(evidence_ids))

    def _task_id_for_task_spec(self, task_spec: TaskSpec) -> str:
        """Identify the canonical logical TaskSpec, not a future execution attempt."""

        payload = task_spec.model_dump(
            exclude={"task_id"},
            mode="json",
            round_trip=True,
        )
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return f"task-{digest}"
