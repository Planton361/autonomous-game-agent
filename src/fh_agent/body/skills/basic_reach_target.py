from dataclasses import dataclass, field
from math import hypot, isfinite

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.manager.reward_computer import RewardComputer, RewardProfile
from fh_agent.manager.skill_contracts import SkillContract, SkillStep, merged_evidence_ids
from fh_agent.manager.target_ref import VisibleScreenPointTarget
from fh_agent.observation.schemas import Observation, SkillResult


@dataclass(slots=True)
class BasicReachTargetSkill:
    """Universal offline reach-target skill based on visible screen positions."""

    target: VisibleScreenPointTarget | None = None
    tolerance_px: float = 4.0
    max_steps: int = 8
    reward_profile: RewardProfile = field(default_factory=RewardProfile)

    def __post_init__(self) -> None:
        if not isfinite(self.tolerance_px) or self.tolerance_px < 0:
            msg = "tolerance_px must be finite and non-negative"
            raise ValueError(msg)

    @property
    def contract(self) -> SkillContract:
        return SkillContract(
            skill_name="basic_reach_target",
            allowed_actions=[
                PrimitiveAction.MOVE_UP_SHORT,
                PrimitiveAction.MOVE_DOWN_SHORT,
                PrimitiveAction.MOVE_LEFT_SHORT,
                PrimitiveAction.MOVE_RIGHT_SHORT,
                PrimitiveAction.WAIT,
            ],
            preconditions=["reach_target_visible", "player_position_visible"],
            success_detector=["target_reached", "screen_signature_changed"],
            failure_detector=["death_screen", "combat_started", "timeout", "no_progress"],
            max_steps=self.max_steps,
            reward_profile=self.reward_profile,
        )

    def can_start(self, observation: Observation) -> bool:
        return self.target is not None and observation.player_screen_position is not None

    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        if not self.can_start(observation) or self.target is None:
            return SkillStep(
                skill_name=self.contract.skill_name,
                action=PrimitiveAction.WAIT,
                step_index=step_index,
                reason="missing_target_or_position",
                evidence_ids=observation.evidence_ids,
            )

        action = movement_action_toward(
            observation.player_screen_position,
            self.target.screen_position,
        )
        return SkillStep(
            skill_name=self.contract.skill_name,
            action=action,
            step_index=step_index,
            reason="move_toward_visible_target",
            evidence_ids=step_evidence_ids(observation, self.target),
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
        elif after.ui_state == "combat" or after.combat_ui_visible is True:
            success = False
            failure_reason = "combat_started"
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
        if self.target is None:
            return False

        reached = (
            after.player_screen_position is not None
            and distance(after.player_screen_position, self.target.screen_position)
            <= self.tolerance_px
        )
        signature_changed = (
            before.screen_signature is not None
            and after.screen_signature is not None
            and before.screen_signature != after.screen_signature
        )
        return reached or signature_changed


def movement_action_toward(
    current_pos: tuple[int, int],
    target_pos: tuple[int, int],
) -> PrimitiveAction:
    current_x, current_y = current_pos
    target_x, target_y = target_pos
    delta_x = target_x - current_x
    delta_y = target_y - current_y

    if abs(delta_x) >= abs(delta_y):
        if delta_x > 0:
            return PrimitiveAction.MOVE_RIGHT_SHORT
        if delta_x < 0:
            return PrimitiveAction.MOVE_LEFT_SHORT

    if delta_y > 0:
        return PrimitiveAction.MOVE_DOWN_SHORT
    if delta_y < 0:
        return PrimitiveAction.MOVE_UP_SHORT

    return PrimitiveAction.WAIT


def distance(first: tuple[int, int], second: tuple[int, int]) -> float:
    return hypot(second[0] - first[0], second[1] - first[1])


def step_evidence_ids(observation: Observation, target: VisibleScreenPointTarget) -> list[str]:
    evidence_ids = list(observation.evidence_ids)
    for evidence_id in target.evidence_ids:
        if evidence_id not in evidence_ids:
            evidence_ids.append(evidence_id)
    return evidence_ids
