import inspect

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills import continue_dialogue as continue_dialogue_module
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.manager.reward_profiles import (
    RewardProfile,
    RewardTerm,
    default_reward_profile_for_skill,
)
from fh_agent.observation.schemas import Observation


def dialogue_observation(text: str, evidence_id: str | None) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text=text,
        message_window_visible=True,
        evidence_ids=[] if evidence_id is None else [evidence_id],
    )


def test_continue_dialogue_accepts_dialogue_observation() -> None:
    assert ContinueDialogueSkill().can_start(dialogue_observation("Hello", "e1"))


def test_continue_dialogue_rejects_field_observation_as_precondition() -> None:
    observation = Observation(run_id="run-1", ui_state="field", evidence_ids=["e1"])

    assert not ContinueDialogueSkill().can_start(observation)


def test_continue_dialogue_emits_primitive_action_only() -> None:
    skill = ContinueDialogueSkill()
    step = skill.next_action(dialogue_observation("Hello", "e1"), step_index=0)

    assert step.action is PrimitiveAction.CONFIRM
    assert step.model_dump() == {
        "skill_name": "continue_dialogue",
        "action": "confirm",
        "step_index": 0,
        "reason": "dialogue_visible",
        "evidence_ids": ["e1"],
    }


def test_continue_dialogue_waits_when_precondition_is_not_met() -> None:
    skill = ContinueDialogueSkill()
    step = skill.next_action(Observation(run_id="run-1", ui_state="field"), step_index=0)

    assert step.action is PrimitiveAction.WAIT
    assert step.reason == "precondition_not_met"


def test_continue_dialogue_contract_declares_visible_outcome_conditions() -> None:
    contract = ContinueDialogueSkill().contract

    assert contract.success_detector == ["visible_text_changed", "dialogue_closed"]
    assert "new_evidence" not in contract.success_detector
    assert "death_screen" in contract.failure_detector
    assert "timeout" in contract.failure_detector


def test_continue_dialogue_uses_and_preserves_canonical_reward_profile() -> None:
    custom_profile = RewardProfile(
        profile_name="custom_dialogue",
        terms=(RewardTerm(name="skill_success", weight=0.0),),
    )
    default_skill = ContinueDialogueSkill()
    custom_skill = ContinueDialogueSkill(reward_profile=custom_profile)

    assert default_skill.reward_profile == default_reward_profile_for_skill("continue_dialogue")
    assert default_skill.contract.reward_profile == default_skill.reward_profile
    assert custom_skill.contract.reward_profile == custom_profile


def test_runtime_body_skill_has_no_outcome_grading_surface() -> None:
    source = inspect.getsource(continue_dialogue_module)

    assert not hasattr(ContinueDialogueSkill(), "evaluate")
    assert "fh_agent.verifier" not in source
    assert "SkillResult" not in source
