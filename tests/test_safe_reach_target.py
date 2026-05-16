import ast
from pathlib import Path

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.safety_filter import HazardSignal, ScreenPoint
from fh_agent.body.skills.safe_reach_target import (
    SafeReachTargetState,
    choose_safe_reach_action,
)


def point(x: float, y: float) -> ScreenPoint:
    return ScreenPoint(x=x, y=y)


def decide(
    *,
    current: ScreenPoint | None = None,
    target: ScreenPoint,
    hazards: list[HazardSignal] | None = None,
    max_risk_threshold: float = 0.4,
):
    return choose_safe_reach_action(
        SafeReachTargetState(
            current_position=current or point(0, 0),
            target_position=target,
            hazards=hazards or [],
            max_risk_threshold=max_risk_threshold,
            step_size=8.0,
        ),
    )


def hazard(x: float, y: float, *, risk_score: float = 1.0) -> HazardSignal:
    return HazardSignal(position=point(x, y), risk_score=risk_score, influence_radius=16.0)


def test_safe_reach_target_moves_right_when_target_is_right() -> None:
    decision = decide(target=point(24, 0))

    assert decision.action is PrimitiveAction.MOVE_RIGHT_SHORT
    assert not decision.blocked


def test_safe_reach_target_moves_left_when_target_is_left() -> None:
    decision = decide(target=point(-24, 0))

    assert decision.action is PrimitiveAction.MOVE_LEFT_SHORT


def test_safe_reach_target_moves_up_or_down_when_target_is_vertical() -> None:
    assert decide(target=point(0, -24)).action is PrimitiveAction.MOVE_UP_SHORT
    assert decide(target=point(0, 24)).action is PrimitiveAction.MOVE_DOWN_SHORT


def test_safe_reach_target_blocks_direct_high_risk_hazard() -> None:
    decision = decide(target=point(24, 0), hazards=[hazard(8, 0)])

    assert decision.action is not PrimitiveAction.MOVE_RIGHT_SHORT
    assert decision.reason == "move_toward_target_within_risk_limit"


def test_safe_reach_target_chooses_safe_alternative_when_direct_path_is_risky() -> None:
    decision = decide(target=point(24, 0), hazards=[hazard(8, 0)])

    assert decision.action is PrimitiveAction.MOVE_DOWN_SHORT
    assert not decision.blocked


def test_safe_reach_target_waits_blocked_when_all_movement_candidates_are_risky() -> None:
    decision = decide(
        target=point(24, 0),
        hazards=[
            hazard(8, 0),
            hazard(-8, 0),
            hazard(0, 8),
            hazard(0, -8),
        ],
    )

    assert decision.action is PrimitiveAction.WAIT
    assert decision.blocked
    assert decision.reason == "blocked_by_high_risk_entity"


def test_safe_reach_target_respects_max_risk_threshold() -> None:
    loose = decide(
        target=point(24, 0),
        hazards=[hazard(8, 0, risk_score=0.5)],
        max_risk_threshold=0.6,
    )
    strict = decide(
        target=point(24, 0),
        hazards=[hazard(8, 0, risk_score=0.5)],
        max_risk_threshold=0.4,
    )

    assert loose.action is PrimitiveAction.MOVE_RIGHT_SHORT
    assert strict.action is not PrimitiveAction.MOVE_RIGHT_SHORT


def test_safe_reach_target_has_deterministic_tie_breaks() -> None:
    first = decide(target=point(24, 24))
    second = decide(target=point(24, 24))

    assert first.action is PrimitiveAction.MOVE_RIGHT_SHORT
    assert second.action is PrimitiveAction.MOVE_RIGHT_SHORT


def test_safe_reach_target_imports_no_execution_or_stateful_layers() -> None:
    root = Path(__file__).resolve().parents[1]
    checked_files = [
        root / "src/fh_agent/body/safety_filter.py",
        root / "src/fh_agent/body/skills/safe_reach_target.py",
    ]
    forbidden_prefixes = (
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.memory",
        "fh_agent.planner",
        "fh_agent.manager",
        "fh_agent.rl",
    )

    imports: list[str] = []
    for checked_file in checked_files:
        tree = ast.parse(checked_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)

    assert not [
        module
        for module in imports
        if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
    ]
