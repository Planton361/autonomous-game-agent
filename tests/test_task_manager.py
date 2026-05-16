import inspect

import pytest

from fh_agent.manager import task_manager as task_manager_module
from fh_agent.manager.reward_profiles import ALLOWED_REWARD_TERMS
from fh_agent.manager.task_manager import TaskManager, TaskManagerError
from fh_agent.planner.planner_output import PlannerOutput


def valid_planner_payload() -> dict[str, object]:
    return {
        "current_belief_state": [
            {
                "kind": "fact",
                "claim": "A visible message is currently on screen.",
                "evidence_ids": ["shot-1"],
            },
            {
                "kind": "hypothesis",
                "claim": "The visible message may continue.",
                "evidence_ids": [],
            },
        ],
        "open_questions": ["Will the visible text change?"],
        "next_goal": "Continue the visible dialogue until the message changes.",
        "selected_skill": "continue_dialogue",
        "success_condition": ["new_visible_text"],
        "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
        "memory_updates_requested": [
            {
                "claim": "A visible message is currently on screen.",
                "evidence_ids": ["shot-2"],
                "reason": "Observed in the current screenshot.",
            }
        ],
    }


def test_valid_planner_output_creates_valid_task_spec() -> None:
    planner_output = PlannerOutput.model_validate(valid_planner_payload())

    task = TaskManager().create_task_from_planner_output(
        planner_output,
        planner_trace_id="trace-1",
    )

    assert task.selected_skill == "continue_dialogue"
    assert task.goal == planner_output.next_goal
    assert task.target == {"description": planner_output.next_goal}
    assert task.constraints["avoid_known_dangers"] is True
    assert task.success_conditions == ["new_visible_text"]
    assert task.timeout_steps == 6
    assert task.source_evidence_ids == ["shot-1", "shot-2"]
    assert task.planner_trace_id == "trace-1"
    assert {term.name for term in task.reward_profile.terms} <= ALLOWED_REWARD_TERMS


def test_task_manager_task_id_is_deterministic() -> None:
    payload = valid_planner_payload()
    manager = TaskManager()

    first = manager.create_task_from_planner_output(payload)
    second = manager.create_task_from_planner_output(payload)

    assert first.task_id == second.task_id
    assert first.to_deterministic_json() == second.to_deterministic_json()


def test_unknown_selected_skill_is_rejected() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "solve_room_y"

    with pytest.raises(TaskManagerError):
        TaskManager().create_task_from_planner_output(payload)


@pytest.mark.parametrize("selected_skill", ["move_up_short", "confirm", "open_menu"])
def test_primitive_selected_skill_is_rejected(selected_skill: str) -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = selected_skill

    with pytest.raises(TaskManagerError):
        TaskManager().create_task_from_planner_output(payload)


@pytest.mark.parametrize("field_name", ["keys", "key_sequence", "primitive_actions", "actions"])
def test_direct_control_fields_are_rejected(field_name: str) -> None:
    payload = valid_planner_payload()
    payload[field_name] = ["confirm"]

    with pytest.raises(TaskManagerError, match="direct primitive controls"):
        TaskManager().create_task_from_planner_output(payload)


def test_hidden_state_terms_are_rejected() -> None:
    payload = valid_planner_payload()
    payload["next_goal"] = "Inspect hidden map_id."

    with pytest.raises(TaskManagerError, match="hidden-state terms"):
        TaskManager().create_task_from_planner_output(payload)


def test_task_manager_has_no_body_inputexecutor_memory_or_llm_dependency() -> None:
    source = inspect.getsource(task_manager_module)

    assert "fh_agent.body" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game.input_executor" not in source
    assert "fh_agent.memory" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source
