from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.safety_filter import HazardSignal, SafetyFilter, ScreenPoint


def point(x: float, y: float) -> ScreenPoint:
    return ScreenPoint(x=x, y=y)


def test_safety_filter_blocks_actions_at_or_above_threshold() -> None:
    safety_filter = SafetyFilter(max_risk_threshold=0.4, step_size=8.0)

    result = safety_filter.assess_action(
        current_position=point(0, 0),
        action=PrimitiveAction.MOVE_RIGHT_SHORT,
        hazards=[
            HazardSignal(
                position=point(8, 0),
                risk_score=0.4,
                influence_radius=16.0,
            ),
        ],
    )

    assert result.blocked
    assert result.risk_score == 0.4
    assert result.reasons == ["blocked_by_high_risk_entity"]


def test_safety_filter_allows_actions_below_threshold() -> None:
    safety_filter = SafetyFilter(max_risk_threshold=0.6, step_size=8.0)

    result = safety_filter.assess_action(
        current_position=point(0, 0),
        action=PrimitiveAction.MOVE_RIGHT_SHORT,
        hazards=[
            HazardSignal(
                position=point(8, 0),
                risk_score=0.4,
                influence_radius=16.0,
            ),
        ],
    )

    assert not result.blocked
    assert result.reasons == []


def test_safety_filter_wait_has_no_hazard_risk() -> None:
    safety_filter = SafetyFilter(max_risk_threshold=0.1, step_size=8.0)

    result = safety_filter.assess_action(
        current_position=point(0, 0),
        action=PrimitiveAction.WAIT,
        hazards=[
            HazardSignal(
                position=point(0, 0),
                risk_score=1.0,
                influence_radius=16.0,
            ),
        ],
    )

    assert not result.blocked
    assert result.risk_score == 0.0
