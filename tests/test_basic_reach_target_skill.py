import math

import pytest

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.basic_reach_target import BasicReachTargetSkill
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.manager.target_ref import VisibleScreenPointTarget
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation
from fh_agent.verifier.reach_target import ReachTargetVerifier


def observation(
    *,
    pos: tuple[int, int] | None,
    evidence_id: str | None = "e1",
    ui_state: str = "field",
    screen_signature: str | None = None,
    visible_message_text: str | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state=ui_state,  # type: ignore[arg-type]
        player_screen_position=pos,
        screen_signature=screen_signature,
        combat_ui_visible=ui_state == "combat",
        death_screen_visible=ui_state == "death",
        visible_message_text=visible_message_text,
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
    skill = BasicReachTargetSkill(target=target())

    assert skill.can_start(observation(pos=(0, 0)))


def test_basic_reach_target_does_not_start_without_target() -> None:
    skill = BasicReachTargetSkill()

    assert not skill.can_start(observation(pos=(0, 0)))


def test_basic_reach_target_does_not_start_without_current_position() -> None:
    skill = BasicReachTargetSkill(target=target())

    assert not skill.can_start(observation(pos=None))


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


def test_basic_reach_target_succeeds_when_target_is_within_tolerance() -> None:
    skill = BasicReachTargetSkill(target=target(10, 10), tolerance_px=3.0)

    result = skill.evaluate(
        observation(pos=(0, 0), evidence_id="e1"),
        observation(pos=(12, 11), evidence_id="e2"),
        steps_taken=1,
    )

    assert result.success
    assert result.failure_reason is None
    assert result.evidence_ids == ["target-evidence", "e2", "e1"]


def test_basic_reach_target_does_not_succeed_when_screen_signature_changes() -> None:
    skill = BasicReachTargetSkill(target=target(100, 100))

    result = skill.evaluate(
        observation(pos=(0, 0), screen_signature="sig-1"),
        observation(pos=(0, 0), screen_signature="sig-2"),
        steps_taken=1,
    )

    assert not result.success
    assert result.failure_reason is None


def test_basic_reach_target_requires_after_evidence_for_success() -> None:
    result = BasicReachTargetSkill(target=target(10, 10)).evaluate(
        observation(pos=(0, 0), evidence_id="before-evidence"),
        observation(pos=(10, 10), evidence_id=None),
        steps_taken=1,
    )

    assert not result.success
    assert result.failure_reason is None


def test_basic_reach_target_outside_tolerance_is_not_success() -> None:
    result = BasicReachTargetSkill(target=target(10, 10), tolerance_px=1.0).evaluate(
        observation(pos=(0, 0)),
        observation(pos=(12, 10), evidence_id="after-evidence"),
        steps_taken=1,
    )

    assert not result.success


def test_new_evidence_alone_outside_target_is_not_success() -> None:
    result = BasicReachTargetSkill(target=target(100, 100)).evaluate(
        observation(pos=(0, 0), evidence_id="before-evidence"),
        observation(pos=(0, 0), evidence_id="new-evidence"),
        steps_taken=1,
    )

    assert not result.success


def test_visible_text_and_ui_change_outside_target_are_not_success() -> None:
    result = BasicReachTargetSkill(target=target(100, 100)).evaluate(
        observation(pos=(0, 0), ui_state="field", evidence_id="before-evidence"),
        observation(
            pos=(0, 0),
            ui_state="dialogue",
            evidence_id="after-evidence",
            visible_message_text="Changed visible text",
        ),
        steps_taken=1,
    )

    assert not result.success


def test_basic_reach_target_contract_only_advertises_target_reached_success() -> None:
    success_detector = BasicReachTargetSkill(target=target()).contract.success_detector

    assert "target_reached" in success_detector
    assert "screen_signature_changed" not in success_detector


def test_basic_reach_target_times_out_with_no_progress() -> None:
    run = SkillRunner().run(
        BasicReachTargetSkill(target=target(20, 0), max_steps=2),
        [
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(0, 0), evidence_id="e1"),
        ],
        verifier=ReachTargetVerifier(target(20, 0)),
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "timeout"
    assert len(run.steps) == 2


def test_basic_reach_target_fails_on_death_or_combat() -> None:
    death_run = SkillRunner().run(
        BasicReachTargetSkill(target=target(20, 0)),
        [
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(1, 0), evidence_id="e2", ui_state="death"),
        ],
        verifier=ReachTargetVerifier(target(20, 0)),
    )
    combat_run = SkillRunner().run(
        BasicReachTargetSkill(target=target(20, 0)),
        [
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(1, 0), evidence_id="e2", ui_state="combat"),
        ],
        verifier=ReachTargetVerifier(target(20, 0)),
    )

    assert death_run.skill_result.failure_reason == "death_screen"
    assert combat_run.skill_result.failure_reason == "combat_started"


def test_visible_death_without_evidence_does_not_map_to_legacy_death_screen() -> None:
    result = BasicReachTargetSkill(target=target(10, 10)).evaluate(
        observation(pos=(0, 0), evidence_id="before-evidence"),
        observation(pos=(10, 10), evidence_id=None, ui_state="death"),
        steps_taken=1,
    )

    assert not result.success
    assert result.failure_reason is None


def test_verifier_death_takes_priority_over_apparent_reach() -> None:
    result = BasicReachTargetSkill(target=target(10, 10)).evaluate(
        observation(pos=(0, 0), evidence_id="before-evidence"),
        observation(pos=(10, 10), evidence_id="death-evidence", ui_state="death"),
        steps_taken=1,
    )

    assert not result.success
    assert result.failure_reason == "death_screen"
    assert result.evidence_ids == ["death-evidence", "before-evidence"]


def test_basic_reach_target_runs_and_logs_with_skill_runner(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    runner = SkillRunner(event_log_path=event_log_path, run_id="run-1")

    run = runner.run(
        BasicReachTargetSkill(target=target(10, 0), tolerance_px=1.0),
        [
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(10, 0), evidence_id="e2"),
        ],
        verifier=ReachTargetVerifier(target(10, 0), tolerance_px=1.0),
    )

    records = EventLogger(event_log_path, run_id="run-1").read_all()
    assert run.skill_result.success
    assert [step.action for step in run.steps] == [PrimitiveAction.MOVE_RIGHT_SHORT]
    assert run.event_record is not None
    assert records[0].event_type == "skill_result"
    assert records[0].payload["skill_name"] == "basic_reach_target"


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


def test_terminal_verifier_evidence_is_deterministic_and_deduplicated() -> None:
    skill = BasicReachTargetSkill(
        target=VisibleScreenPointTarget(
            target_id="visible-target",
            confidence=0.9,
            screen_position=(10, 10),
            evidence_ids=("target-evidence", "shared"),
        )
    )

    result = skill.evaluate(
        observation(pos=(0, 0), evidence_id="before-evidence"),
        observation(pos=(10, 10), evidence_id="shared"),
        steps_taken=1,
    )

    assert result.evidence_ids == ["target-evidence", "shared", "before-evidence"]


def test_positive_observation_reward_cannot_override_verifier_abstention() -> None:
    result = BasicReachTargetSkill(target=target(100, 100)).evaluate(
        observation(
            pos=(0, 0),
            ui_state="dialogue",
            evidence_id="before-evidence",
            visible_message_text="First line",
        ),
        observation(
            pos=(0, 0),
            ui_state="dialogue",
            evidence_id="after-evidence",
            visible_message_text="Second line",
        ),
        steps_taken=1,
    )

    assert result.reward is not None and result.reward > 0
    assert not result.success


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
