from math import hypot

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.body.primitive_actions import PrimitiveAction


class ScreenPoint(BaseModel):
    """Synthetic visible-screen coordinate."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float

    def moved_by(self, *, dx: float, dy: float) -> "ScreenPoint":
        return ScreenPoint(x=self.x + dx, y=self.y + dy)


class HazardSignal(BaseModel):
    """Synthetic risk signal derived from visible evidence outside this module."""

    model_config = ConfigDict(extra="forbid")

    position: ScreenPoint
    risk_score: float = Field(ge=0.0, le=1.0)
    influence_radius: float = Field(default=16.0, gt=0.0)
    evidence_ids: list[str] = Field(default_factory=list)


class SafetyFilterResult(BaseModel):
    """Deterministic safety assessment for one primitive candidate."""

    model_config = ConfigDict(extra="forbid")

    action: PrimitiveAction
    risk_score: float
    blocked: bool
    reasons: list[str] = Field(default_factory=list)


ACTION_DELTAS: dict[PrimitiveAction, tuple[float, float]] = {
    PrimitiveAction.MOVE_UP_SHORT: (0.0, -1.0),
    PrimitiveAction.MOVE_DOWN_SHORT: (0.0, 1.0),
    PrimitiveAction.MOVE_LEFT_SHORT: (-1.0, 0.0),
    PrimitiveAction.MOVE_RIGHT_SHORT: (1.0, 0.0),
}


class SafetyFilter(BaseModel):
    """Pure risk filter for synthetic movement candidates."""

    model_config = ConfigDict(extra="forbid")

    max_risk_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    step_size: float = Field(default=8.0, gt=0.0)

    def assess_action(
        self,
        *,
        current_position: ScreenPoint,
        action: PrimitiveAction,
        hazards: list[HazardSignal],
    ) -> SafetyFilterResult:
        if action is PrimitiveAction.WAIT:
            return SafetyFilterResult(action=action, risk_score=0.0, blocked=False)

        if action not in ACTION_DELTAS:
            return SafetyFilterResult(
                action=action,
                risk_score=1.0,
                blocked=True,
                reasons=["unsupported_navigation_action"],
            )

        next_position = next_position_for_action(
            current_position,
            action,
            step_size=self.step_size,
        )
        risk_score = max(
            (hazard_risk_at_point(hazard, next_position) for hazard in hazards),
            default=0.0,
        )
        blocked = risk_score >= self.max_risk_threshold
        reasons = ["blocked_by_high_risk_entity"] if blocked else []
        return SafetyFilterResult(
            action=action,
            risk_score=risk_score,
            blocked=blocked,
            reasons=reasons,
        )

    def assess_actions(
        self,
        *,
        current_position: ScreenPoint,
        actions: list[PrimitiveAction],
        hazards: list[HazardSignal],
    ) -> list[SafetyFilterResult]:
        return [
            self.assess_action(
                current_position=current_position,
                action=action,
                hazards=hazards,
            )
            for action in actions
        ]


def next_position_for_action(
    current_position: ScreenPoint,
    action: PrimitiveAction,
    *,
    step_size: float,
) -> ScreenPoint:
    dx, dy = ACTION_DELTAS[action]
    return current_position.moved_by(dx=dx * step_size, dy=dy * step_size)


def hazard_risk_at_point(hazard: HazardSignal, point: ScreenPoint) -> float:
    distance = point_distance(point, hazard.position)
    if distance > hazard.influence_radius:
        return 0.0
    return hazard.risk_score * (1.0 - (distance / hazard.influence_radius))


def point_distance(first: ScreenPoint, second: ScreenPoint) -> float:
    return hypot(second.x - first.x, second.y - first.y)
