from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.basic_reach_target import BasicReachTargetSkill, ScreenTarget
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation


def observation(
    *,
    pos: tuple[int, int] | None,
    evidence_id: str = "e1",
    ui_state: str = "field",
    screen_signature: str | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state=ui_state,  # type: ignore[arg-type]
        player_screen_position=pos,
        screen_signature=screen_signature,
        combat_ui_visible=ui_state == "combat",
        death_screen_visible=ui_state == "death",
        evidence_ids=[evidence_id],
    )


def target(x: int = 20, y: int = 10, *, tolerance_px: float = 2.0) -> ScreenTarget:
    return ScreenTarget(
        target_id="visible-target",
        target_screen_pos=(x, y),
        tolerance_px=tolerance_px,
        evidence_ids=["target-evidence"],
    )


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
        BasicReachTargetSkill(target=target(-10, 0))
        .next_action(observation(pos=(0, 0)), step_index=0)
        .action
        is PrimitiveAction.MOVE_LEFT_SHORT
    )
    assert (
        BasicReachTargetSkill(target=target(0, -10))
        .next_action(observation(pos=(0, 0)), step_index=0)
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
    skill = BasicReachTargetSkill(target=target(10, 10, tolerance_px=3.0))

    result = skill.evaluate(
        observation(pos=(0, 0), evidence_id="e1"),
        observation(pos=(12, 11), evidence_id="e2"),
        steps_taken=1,
    )

    assert result.success
    assert result.failure_reason is None
    assert result.evidence_ids == ["e1", "e2"]


def test_basic_reach_target_succeeds_when_screen_signature_changes() -> None:
    skill = BasicReachTargetSkill(target=target(100, 100))

    result = skill.evaluate(
        observation(pos=(0, 0), screen_signature="sig-1"),
        observation(pos=(0, 0), screen_signature="sig-2"),
        steps_taken=1,
    )

    assert result.success


def test_basic_reach_target_times_out_with_no_progress() -> None:
    run = SkillRunner().run(
        BasicReachTargetSkill(target=target(20, 0), max_steps=2),
        [
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(0, 0), evidence_id="e1"),
        ],
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
    )
    combat_run = SkillRunner().run(
        BasicReachTargetSkill(target=target(20, 0)),
        [
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(1, 0), evidence_id="e2", ui_state="combat"),
        ],
    )

    assert death_run.skill_result.failure_reason == "death_screen"
    assert combat_run.skill_result.failure_reason == "combat_started"


def test_basic_reach_target_runs_and_logs_with_skill_runner(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    runner = SkillRunner(event_log_path=event_log_path, run_id="run-1")

    run = runner.run(
        BasicReachTargetSkill(target=target(10, 0, tolerance_px=1.0)),
        [
            observation(pos=(0, 0), evidence_id="e1"),
            observation(pos=(10, 0), evidence_id="e2"),
        ],
    )

    records = EventLogger(event_log_path, run_id="run-1").read_all()
    assert run.skill_result.success
    assert [step.action for step in run.steps] == [PrimitiveAction.MOVE_RIGHT_SHORT]
    assert run.event_record is not None
    assert records[0].event_type == "skill_result"
    assert records[0].payload["skill_name"] == "basic_reach_target"
