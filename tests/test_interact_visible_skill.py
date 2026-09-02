import inspect

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills import interact_visible as interact_visible_module
from fh_agent.body.skills.interact_visible import InteractVisibleObjectSkill
from fh_agent.manager.target_ref import VisibleObjectTarget
from fh_agent.observation.schemas import Observation


def field_observation(
    *,
    evidence_id: str | None = "e1",
    visible_target: bool = False,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="field",
        visible_sprite_screen_positions=[(10, 20)] if visible_target else [],
        evidence_ids=[] if evidence_id is None else [evidence_id],
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
    assert not InteractVisibleObjectSkill().can_start(field_observation())


def test_interact_visible_starts_with_canonical_explicit_target() -> None:
    target = visible_object_target()
    skill = InteractVisibleObjectSkill(target=target)

    assert skill.can_start(field_observation())
    assert skill.target is target


def test_interact_visible_starts_from_visible_candidate_without_explicit_target() -> None:
    assert InteractVisibleObjectSkill().can_start(field_observation(visible_target=True))


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


def test_interact_visible_contract_declares_supported_outcome_conditions() -> None:
    contract = InteractVisibleObjectSkill().contract

    assert contract.success_detector == ["dialogue_visible", "interaction_outcome_visible"]
    assert "screen_signature_changed" not in contract.success_detector
    assert "new_evidence" not in contract.success_detector
    assert "death_screen" in contract.failure_detector


def test_runtime_body_skill_has_no_outcome_grading_surface() -> None:
    source = inspect.getsource(interact_visible_module)

    assert not hasattr(InteractVisibleObjectSkill(), "evaluate")
    assert "fh_agent.verifier" not in source
    assert "RewardComputer" not in source
    assert "SkillResult" not in source
