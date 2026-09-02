import inspect

import pytest
from pydantic import ValidationError

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills import (
    basic_reach_target,
    continue_dialogue,
    interact_visible,
)
from fh_agent.manager.reward_profiles import RewardProfile, RewardTerm
from fh_agent.manager.skill_contracts import SkillContract, SkillStep
from fh_agent.manager.task_spec import TaskSpec

TEST_REWARD_PROFILE = RewardProfile(
    profile_name="test_profile",
    terms=(RewardTerm(name="skill_success", weight=0.0),),
)


def test_skill_contract_declares_success_and_failure_detectors() -> None:
    contract = SkillContract(
        skill_name="continue_dialogue",
        allowed_actions=[PrimitiveAction.CONFIRM, PrimitiveAction.WAIT],
        preconditions=["dialogue_visible"],
        success_detector=["visible_text_changed", "dialogue_closed"],
        failure_detector=["timeout"],
        max_steps=3,
        reward_profile=TEST_REWARD_PROFILE,
    )

    assert contract.success_detector == ["visible_text_changed", "dialogue_closed"]
    assert contract.failure_detector == ["timeout"]
    assert contract.max_steps == 3
    assert contract.reward_profile == TEST_REWARD_PROFILE
    assert isinstance(contract.reward_profile, RewardProfile)


def test_skill_contract_rejects_unknown_primitive_action() -> None:
    with pytest.raises(ValidationError):
        SkillContract(
            skill_name="bad_skill",
            allowed_actions=["press_f13"],
            preconditions=["dialogue_visible"],
            success_detector=["visible_text_changed"],
            failure_detector=["timeout"],
            max_steps=1,
            reward_profile=TEST_REWARD_PROFILE,
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


def test_skill_contract_requires_a_canonical_reward_profile() -> None:
    with pytest.raises(ValidationError, match="reward_profile"):
        SkillContract(
            skill_name="missing_profile",
            allowed_actions=[PrimitiveAction.WAIT],
            preconditions=["dialogue_visible"],
            success_detector=["dialogue_visible"],
            failure_detector=["timeout"],
            max_steps=1,
        )


def test_skill_contract_rejects_legacy_observation_weight_profile_payload() -> None:
    with pytest.raises(ValidationError):
        SkillContract(
            skill_name="legacy_profile",
            allowed_actions=[PrimitiveAction.WAIT],
            preconditions=["dialogue_visible"],
            success_detector=["dialogue_visible"],
            failure_detector=["timeout"],
            max_steps=1,
            reward_profile={
                "dialogue_continued": 1.0,
                "visible_text_changed": 0.5,
                "ui_state_changed": 0.25,
            },
        )


def test_task_spec_and_skill_contract_share_the_canonical_reward_profile_type() -> None:
    task = TaskSpec(
        task_id="task-1",
        selected_skill="continue_dialogue",
        goal="Continue visible dialogue.",
        timeout_steps=3,
        reward_profile=TEST_REWARD_PROFILE,
    )
    contract = SkillContract(
        skill_name="custom_skill",
        allowed_actions=[PrimitiveAction.WAIT],
        preconditions=["dialogue_visible"],
        success_detector=["dialogue_visible"],
        failure_detector=["timeout"],
        max_steps=1,
        reward_profile=task.reward_profile,
    )

    assert isinstance(task.reward_profile, RewardProfile)
    assert contract.reward_profile == task.reward_profile


def test_runtime_body_skills_do_not_import_the_legacy_reward_profile() -> None:
    legacy_module = "fh_agent.manager.reward_computer"

    assert all(
        legacy_module not in inspect.getsource(module)
        for module in (basic_reach_target, continue_dialogue, interact_visible)
    )
