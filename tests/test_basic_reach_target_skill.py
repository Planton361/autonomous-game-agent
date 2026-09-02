import inspect
import math

import pytest

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills import basic_reach_target as basic_reach_target_module
from fh_agent.body.skills.basic_reach_target import BasicReachTargetSkill
from fh_agent.manager.target_ref import VisibleScreenPointTarget
from fh_agent.observation.schemas import Observation


def observation(*, pos: tuple[int, int] | None, evidence_id: str | None = "e1") -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="field",
        player_screen_position=pos,
        evidence_ids=[] if evidence_id is None else [evidence_id],
    )


def target(x: int = 20, y: int = 10) -> VisibleScreenPointTarget:
    return VisibleScreenPointTarget(
        target_id="visible-target",
        confidence=0.9,
        screen_position=(x, y),
        evidence_ids=("target-evidence",),
    )


def test_basic_reach_target_accepts_canonical_visible_screen_point_target() -> None:
    grounded_target = target()
    skill = BasicReachTargetSkill(target=grounded_target)

    assert skill.target is grounded_target


def test_basic_reach_target_starts_with_canonical_target_and_visible_position() -> None:
    assert BasicReachTargetSkill(target=target()).can_start(observation(pos=(0, 0)))


def test_basic_reach_target_does_not_start_without_target() -> None:
    assert not BasicReachTargetSkill().can_start(observation(pos=(0, 0)))


def test_basic_reach_target_does_not_start_without_current_position() -> None:
    assert not BasicReachTargetSkill(target=target()).can_start(observation(pos=None))


def test_basic_reach_target_emits_only_allowed_movement_or_wait_actions() -> None:
    skill = BasicReachTargetSkill(target=target(10, 0))

    move_step = skill.next_action(observation(pos=(0, 0)), step_index=0)
    wait_step = BasicReachTargetSkill(target=target()).next_action(
        observation(pos=None),
        step_index=1,
    )

    assert move_step.action is PrimitiveAction.MOVE_RIGHT_SHORT
    assert wait_step.action is PrimitiveAction.WAIT
    assert {move_step.action, wait_step.action} <= set(skill.contract.allowed_actions)
    assert "key_sequence" not in move_step.model_dump()


def test_basic_reach_target_moves_right_left_up_and_down() -> None:
    assert (
        BasicReachTargetSkill(target=target(10, 0))
        .next_action(observation(pos=(0, 0)), step_index=0)
        .action
        is PrimitiveAction.MOVE_RIGHT_SHORT
    )
    assert (
        BasicReachTargetSkill(target=target(10, 0))
        .next_action(observation(pos=(20, 0)), step_index=0)
        .action
        is PrimitiveAction.MOVE_LEFT_SHORT
    )
    assert (
        BasicReachTargetSkill(target=target(0, 10))
        .next_action(observation(pos=(0, 20)), step_index=0)
        .action
        is PrimitiveAction.MOVE_UP_SHORT
    )
    assert (
        BasicReachTargetSkill(target=target(0, 10))
        .next_action(observation(pos=(0, 0)), step_index=0)
        .action
        is PrimitiveAction.MOVE_DOWN_SHORT
    )


def test_basic_reach_target_prefers_axis_with_larger_delta() -> None:
    horizontal = BasicReachTargetSkill(target=target(20, 5)).next_action(
        observation(pos=(0, 0)),
        step_index=0,
    )
    vertical = BasicReachTargetSkill(target=target(5, 20)).next_action(
        observation(pos=(0, 0)),
        step_index=0,
    )

    assert horizontal.action is PrimitiveAction.MOVE_RIGHT_SHORT
    assert vertical.action is PrimitiveAction.MOVE_DOWN_SHORT


def test_basic_reach_target_contract_declares_body_execution_constraints() -> None:
    contract = BasicReachTargetSkill(target=target()).contract

    assert contract.success_detector == ["target_reached"]
    assert "screen_signature_changed" not in contract.success_detector
    assert "death_screen" in contract.failure_detector
    assert "combat_started" in contract.failure_detector


def test_basic_reach_target_step_preserves_observation_and_target_evidence() -> None:
    skill = BasicReachTargetSkill(
        target=VisibleScreenPointTarget(
            target_id="visible-target",
            confidence=0.9,
            screen_position=(10, 0),
            evidence_ids=("shared", "target-evidence"),
        )
    )

    step = skill.next_action(
        observation(pos=(0, 0), evidence_id="shared"),
        step_index=0,
    )

    assert step.evidence_ids == ["shared", "target-evidence"]


@pytest.mark.parametrize("tolerance_px", [0.0, 1.5])
def test_basic_reach_target_accepts_finite_non_negative_tolerance(tolerance_px: float) -> None:
    skill = BasicReachTargetSkill(target=target(), tolerance_px=tolerance_px)

    assert skill.tolerance_px == tolerance_px


def test_basic_reach_target_rejects_negative_tolerance() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        BasicReachTargetSkill(target=target(), tolerance_px=-0.1)


@pytest.mark.parametrize("tolerance_px", [math.inf, -math.inf, math.nan])
def test_basic_reach_target_rejects_non_finite_tolerance(tolerance_px: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        BasicReachTargetSkill(target=target(), tolerance_px=tolerance_px)


def test_runtime_body_skill_has_no_outcome_grading_surface() -> None:
    source = inspect.getsource(basic_reach_target_module)

    assert not hasattr(BasicReachTargetSkill(), "evaluate")
    assert "fh_agent.verifier" not in source
    assert "RewardComputer" not in source
    assert "SkillResult" not in source
