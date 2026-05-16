import json

import pytest
from pydantic import ValidationError

from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.task_spec import TaskSpec


def valid_task_spec_payload() -> dict[str, object]:
    return {
        "task_id": "task-1",
        "selected_skill": "continue_dialogue",
        "goal": "Continue the visible dialogue.",
        "target": {"description": "visible dialogue"},
        "constraints": {"avoid_known_dangers": True, "max_danger_score": 0.4},
        "success_conditions": ["new_visible_text"],
        "failure_conditions": ["death_screen", "timeout"],
        "timeout_steps": 6,
        "reward_profile": default_reward_profile_for_skill("continue_dialogue"),
        "source_evidence_ids": ["shot-1"],
        "planner_trace_id": "trace-1",
    }


def test_task_spec_accepts_valid_contract() -> None:
    task = TaskSpec.model_validate(valid_task_spec_payload())

    assert task.selected_skill == "continue_dialogue"
    assert task.reward_profile.profile_name == "continue_dialogue_default"
    assert task.source_evidence_ids == ["shot-1"]


def test_task_spec_serializes_deterministically() -> None:
    task = TaskSpec.model_validate(valid_task_spec_payload())

    first = task.to_deterministic_json()
    second = task.to_deterministic_json()

    assert first == second
    assert json.loads(first)["task_id"] == "task-1"
    assert list(json.loads(first)) == sorted(json.loads(first))


@pytest.mark.parametrize("selected_skill", ["move_up_short", "confirm", "open_menu"])
def test_task_spec_rejects_primitive_selected_skill(selected_skill: str) -> None:
    payload = valid_task_spec_payload()
    payload["selected_skill"] = selected_skill

    with pytest.raises(ValidationError):
        TaskSpec.model_validate(payload)


@pytest.mark.parametrize("field_name", ["keys", "key_sequence", "primitive_actions", "actions"])
def test_task_spec_rejects_direct_control_fields(field_name: str) -> None:
    payload = valid_task_spec_payload()
    payload[field_name] = ["confirm"]

    with pytest.raises(ValidationError, match="direct primitive controls"):
        TaskSpec.model_validate(payload)


def test_task_spec_rejects_hidden_state_terms() -> None:
    payload = valid_task_spec_payload()
    payload["goal"] = "Use map_id from hidden state."

    with pytest.raises(ValidationError, match="hidden-state terms"):
        TaskSpec.model_validate(payload)
