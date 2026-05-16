from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.safety_filter import (
    ACTION_DELTAS,
    HazardSignal,
    SafetyFilter,
    ScreenPoint,
    next_position_for_action,
    point_distance,
)


class SafeReachTargetState(BaseModel):
    """Synthetic state for one safe-reach-target planning step."""

    model_config = ConfigDict(extra="forbid")

    current_position: ScreenPoint
    target_position: ScreenPoint
    hazards: list[HazardSignal] = Field(default_factory=list)
    max_risk_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    step_size: float = Field(default=8.0, gt=0.0)


class SafeReachTargetDecision(BaseModel):
    """Pure navigation decision with scoring details for tests and logs."""

    model_config = ConfigDict(extra="forbid")

    action: PrimitiveAction
    blocked: bool = False
    reason: str
    risk_score: float = Field(ge=0.0, le=1.0)
    target_distance_after_action: float
    considered_actions: list[PrimitiveAction]


class SafeReachTargetSkillResult(BaseModel):
    """Skill wrapper result that does not execute the chosen primitive action."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str
    action: PrimitiveAction
    decision: SafeReachTargetDecision
    blocked_by_high_risk_entity: bool


NAVIGATION_ACTIONS: tuple[PrimitiveAction, ...] = (
    PrimitiveAction.MOVE_RIGHT_SHORT,
    PrimitiveAction.MOVE_LEFT_SHORT,
    PrimitiveAction.MOVE_DOWN_SHORT,
    PrimitiveAction.MOVE_UP_SHORT,
)


@dataclass(frozen=True, slots=True)
class SafeReachTargetSkill:
    """Small Body skill wrapper around the pure safe-reach planning core."""

    skill_name: str = "safe_reach_target"

    def decide_next_action(self, state: SafeReachTargetState) -> SafeReachTargetSkillResult:
        decision = choose_safe_reach_action(state)
        return SafeReachTargetSkillResult(
            skill_name=self.skill_name,
            action=decision.action,
            decision=decision,
            blocked_by_high_risk_entity=decision.reason == "blocked_by_high_risk_entity",
        )


def choose_safe_reach_action(state: SafeReachTargetState) -> SafeReachTargetDecision:
    safety_filter = SafetyFilter(
        max_risk_threshold=state.max_risk_threshold,
        step_size=state.step_size,
    )
    safety_results = {
        result.action: result
        for result in safety_filter.assess_actions(
            current_position=state.current_position,
            actions=list(NAVIGATION_ACTIONS),
            hazards=state.hazards,
        )
    }

    safe_candidates = [
        action for action in NAVIGATION_ACTIONS if not safety_results[action].blocked
    ]
    considered_actions = list(NAVIGATION_ACTIONS)

    if not safe_candidates:
        worst_block = max(safety_results.values(), key=lambda result: result.risk_score)
        return SafeReachTargetDecision(
            action=PrimitiveAction.WAIT,
            blocked=True,
            reason=worst_block.reasons[0] if worst_block.reasons else "blocked_by_high_risk_entity",
            risk_score=worst_block.risk_score,
            target_distance_after_action=point_distance(
                state.current_position,
                state.target_position,
            ),
            considered_actions=considered_actions,
        )

    best_action = min(
        safe_candidates,
        key=lambda action: _candidate_sort_key(state, safety_results[action].risk_score, action),
    )
    best_result = safety_results[best_action]
    return SafeReachTargetDecision(
        action=best_action,
        blocked=False,
        reason="move_toward_target_within_risk_limit",
        risk_score=best_result.risk_score,
        target_distance_after_action=_distance_after_action(state, best_action),
        considered_actions=considered_actions,
    )


def _candidate_sort_key(
    state: SafeReachTargetState,
    risk_score: float,
    action: PrimitiveAction,
) -> tuple[float, float, int]:
    return (
        _distance_after_action(state, action),
        risk_score,
        NAVIGATION_ACTIONS.index(action),
    )


def _distance_after_action(
    state: SafeReachTargetState,
    action: PrimitiveAction,
) -> float:
    if action not in ACTION_DELTAS:
        return point_distance(state.current_position, state.target_position)
    return point_distance(
        next_position_for_action(
            state.current_position,
            action,
            step_size=state.step_size,
        ),
        state.target_position,
    )
