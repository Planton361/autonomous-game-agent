import pytest
from pydantic import ValidationError

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.manager.skill_contracts import SkillContract, SkillStep


def test_skill_contract_declares_success_and_failure_detectors() -> None:
    contract = SkillContract(
        skill_name="continue_dialogue",
        allowed_actions=[PrimitiveAction.CONFIRM, PrimitiveAction.WAIT],
        preconditions=["dialogue_visible"],
        success_detector=["visible_text_changed", "dialogue_closed"],
        failure_detector=["timeout"],
        max_steps=3,
    )

    assert contract.success_detector == ["visible_text_changed", "dialogue_closed"]
    assert contract.failure_detector == ["timeout"]
    assert contract.max_steps == 3


def test_skill_contract_rejects_unknown_primitive_action() -> None:
    with pytest.raises(ValidationError):
        SkillContract(
            skill_name="bad_skill",
            allowed_actions=["press_f13"],
            preconditions=["dialogue_visible"],
            success_detector=["visible_text_changed"],
            failure_detector=["timeout"],
            max_steps=1,
        )


def test_skill_step_does_not_allow_key_sequences() -> None:
    with pytest.raises(ValidationError):
        SkillStep(
            skill_name="continue_dialogue",
            action=PrimitiveAction.CONFIRM,
            step_index=0,
            reason="dialogue_visible",
            key_sequence=["enter"],
        )
