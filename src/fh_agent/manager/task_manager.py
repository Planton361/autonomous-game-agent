import hashlib
import json
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.planner.planner_output import (
    PRIMITIVE_ACTION_NAMES,
    PlannerOutput,
    find_direct_control_violations,
    find_hidden_state_term_violations,
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


class TaskManager:
    """Pure translator from validated planner intent to TaskSpec contracts."""

    def create_task_from_planner_output(
        self,
        planner_output: PlannerOutput | Mapping[str, Any],
        *,
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

        reward_profile = default_reward_profile_for_skill(selected_skill)
        timeout_steps = DEFAULT_TIMEOUT_STEPS.get(selected_skill, 60)
        task_payload = {
            "task_id": self._task_id_for_payload(output_payload),
            "selected_skill": selected_skill,
            "goal": output.next_goal,
            "target": {"description": output.next_goal},
            "constraints": {
                "avoid_known_dangers": output.risk_limit.avoid_known_dangers,
                "max_danger_score": output.risk_limit.max_danger_score,
            },
            "success_conditions": list(output.success_condition),
            "failure_conditions": list(DEFAULT_FAILURE_CONDITIONS),
            "timeout_steps": timeout_steps,
            "reward_profile": reward_profile,
            "source_evidence_ids": self._source_evidence_ids(output),
            "planner_output_id": planner_output_id,
            "planner_trace_id": planner_trace_id,
        }
        return TaskSpec.model_validate(task_payload)

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

    def _source_evidence_ids(self, planner_output: PlannerOutput) -> list[str]:
        evidence_ids: list[str] = []
        for claim in planner_output.current_belief_state:
            for evidence_id in claim.evidence_ids:
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
        for update in planner_output.memory_updates_requested:
            for evidence_id in update.evidence_ids:
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
        return evidence_ids

    def _task_id_for_payload(self, payload: Mapping[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return f"task-{digest}"
