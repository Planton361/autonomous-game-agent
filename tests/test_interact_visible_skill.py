from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.interact_visible import InteractVisibleObjectSkill
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.manager.target_ref import VisibleObjectTarget
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation


def field_observation(
    *,
    evidence_id: str = "e1",
    visible_target: bool = False,
    visible_text: str | None = None,
    screen_signature: str | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="field",
        visible_message_text=visible_text,
        screen_signature=screen_signature,
        visible_sprite_screen_positions=[(10, 20)] if visible_target else [],
        evidence_ids=[evidence_id],
    )


def visible_object_target(
    *, evidence_ids: tuple[str, ...] = ("target-evidence",)
) -> VisibleObjectTarget:
    return VisibleObjectTarget(
        target_id="visible-object",
        confidence=0.9,
        evidence_ids=evidence_ids,
        screen_position=(10, 20),
        visual_hash="visible-hash",
    )


def test_interact_visible_does_not_start_without_visible_target() -> None:
    skill = InteractVisibleObjectSkill()

    assert not skill.can_start(field_observation())


def test_interact_visible_starts_with_canonical_explicit_target() -> None:
    target = visible_object_target()
    skill = InteractVisibleObjectSkill(target=target)

    assert skill.can_start(field_observation())
    assert skill.target is target


def test_explicit_target_confirm_step_preserves_observation_and_target_evidence() -> None:
    target = visible_object_target(evidence_ids=("observation-evidence", "target-evidence"))
    skill = InteractVisibleObjectSkill(target=target)

    step = skill.next_action(field_observation(evidence_id="observation-evidence"), step_index=0)

    assert step.action is PrimitiveAction.CONFIRM
    assert step.evidence_ids == ["observation-evidence", "target-evidence"]


def test_interact_visible_emits_only_confirm_or_wait() -> None:
    skill = InteractVisibleObjectSkill()

    confirm_step = skill.next_action(
        field_observation(visible_target=True),
        step_index=0,
    )
    wait_step = skill.next_action(field_observation(), step_index=1)

    assert confirm_step.action is PrimitiveAction.CONFIRM
    assert wait_step.action is PrimitiveAction.WAIT
    assert {confirm_step.action, wait_step.action} <= {
        PrimitiveAction.CONFIRM,
        PrimitiveAction.WAIT,
    }
    assert "key_sequence" not in confirm_step.model_dump()


def test_interact_visible_succeeds_when_dialogue_appears() -> None:
    run = SkillRunner().run(
        InteractVisibleObjectSkill(),
        [
            field_observation(visible_target=True, evidence_id="e1"),
            Observation(run_id="run-1", ui_state="dialogue", evidence_ids=["e2"]),
        ],
    )

    assert run.skill_result.success
    assert run.skill_result.failure_reason is None
    assert [step.action for step in run.steps] == [PrimitiveAction.CONFIRM]


def test_interact_visible_succeeds_when_visible_text_changes() -> None:
    skill = InteractVisibleObjectSkill()

    result = skill.evaluate(
        field_observation(visible_target=True, visible_text="Look", evidence_id="e1"),
        field_observation(visible_target=True, visible_text="Changed", evidence_id="e2"),
        steps_taken=1,
    )

    assert result.success
    assert result.evidence_ids == ["e1", "e2"]


def test_interact_visible_succeeds_when_screen_signature_changes() -> None:
    skill = InteractVisibleObjectSkill()

    result = skill.evaluate(
        field_observation(visible_target=True, screen_signature="sig-1", evidence_id="e1"),
        field_observation(visible_target=True, screen_signature="sig-2", evidence_id="e2"),
        steps_taken=1,
    )

    assert result.success
    assert result.failure_reason is None


def test_interact_visible_fails_on_timeout_with_no_visible_change() -> None:
    run = SkillRunner().run(
        InteractVisibleObjectSkill(max_steps=2),
        [
            field_observation(visible_target=True, evidence_id="e1", screen_signature="same"),
            field_observation(visible_target=True, evidence_id="e1", screen_signature="same"),
            field_observation(visible_target=True, evidence_id="e1", screen_signature="same"),
        ],
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "timeout"
    assert len(run.steps) == 2


def test_interact_visible_fails_when_death_screen_appears() -> None:
    run = SkillRunner().run(
        InteractVisibleObjectSkill(),
        [
            field_observation(visible_target=True, evidence_id="e1"),
            Observation(
                run_id="run-1", ui_state="death", death_screen_visible=True, evidence_ids=["e2"]
            ),
        ],
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "death_screen"


def test_interact_visible_logs_skill_result_with_skill_runner(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    runner = SkillRunner(event_log_path=event_log_path, run_id="run-1")

    run = runner.run(
        InteractVisibleObjectSkill(),
        [
            field_observation(visible_target=True, evidence_id="e1"),
            Observation(run_id="run-1", ui_state="menu", evidence_ids=["e2"]),
        ],
    )

    records = EventLogger(event_log_path, run_id="run-1").read_all()
    assert run.skill_result.success
    assert run.event_record is not None
    assert records[0].event_type == "skill_result"
    assert records[0].payload["skill_name"] == "interact_visible_object"
