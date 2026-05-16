import ast
from pathlib import Path

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.safety_filter import HazardSignal, ScreenPoint
from fh_agent.body.skills.safe_reach_target import (
    SafeReachTargetSkill,
    SafeReachTargetState,
    choose_safe_reach_action,
)


def point(x: float, y: float) -> ScreenPoint:
    return ScreenPoint(x=x, y=y)


def hazard(x: float, y: float) -> HazardSignal:
    return HazardSignal(position=point(x, y), risk_score=1.0, influence_radius=16.0)


def state(
    *,
    target: ScreenPoint,
    hazards: list[HazardSignal] | None = None,
) -> SafeReachTargetState:
    return SafeReachTargetState(
        current_position=point(0, 0),
        target_position=target,
        hazards=hazards or [],
        max_risk_threshold=0.4,
        step_size=8.0,
    )


def test_safe_reach_target_skill_returns_same_decision_as_planning_core() -> None:
    synthetic_state = state(target=point(24, 0))

    core_decision = choose_safe_reach_action(synthetic_state)
    skill_result = SafeReachTargetSkill().decide_next_action(synthetic_state)

    assert skill_result.decision == core_decision
    assert skill_result.action is core_decision.action
    assert skill_result.action is PrimitiveAction.MOVE_RIGHT_SHORT


def test_safe_reach_target_skill_reports_high_risk_block() -> None:
    synthetic_state = state(
        target=point(24, 0),
        hazards=[
            hazard(8, 0),
            hazard(-8, 0),
            hazard(0, 8),
            hazard(0, -8),
        ],
    )

    skill_result = SafeReachTargetSkill().decide_next_action(synthetic_state)

    assert skill_result.action is PrimitiveAction.WAIT
    assert skill_result.blocked_by_high_risk_entity is True
    assert skill_result.decision.reason == "blocked_by_high_risk_entity"


def test_safe_reach_target_skill_does_not_execute_actions() -> None:
    skill_result = SafeReachTargetSkill().decide_next_action(state(target=point(-24, 0)))

    assert skill_result.action is PrimitiveAction.MOVE_LEFT_SHORT
    assert "key_sequence" not in skill_result.model_dump()
    assert "executed" not in skill_result.model_dump()


def test_safe_reach_target_skill_imports_no_execution_or_stateful_layers() -> None:
    root = Path(__file__).resolve().parents[1]
    checked_file = root / "src/fh_agent/body/skills/safe_reach_target.py"
    forbidden_prefixes = (
        "fh_agent.game",
        "fh_agent.game.input_executor",
        "fh_agent.bridge",
        "fh_agent.memory",
        "fh_agent.planner",
        "fh_agent.rl",
    )

    imports: list[str] = []
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
