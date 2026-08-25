import inspect

import pytest

from fh_agent.manager import task_manager as task_manager_module
from fh_agent.manager.reward_profiles import ALLOWED_REWARD_TERMS
from fh_agent.manager.skill_target_requirements import target_requirement_for_skill
from fh_agent.manager.target_ref import (
    GroundingResult,
    VisibleObjectTarget,
    VisibleScreenPointTarget,
)
from fh_agent.manager.task_manager import (
    ManagerGroundingError,
    TaskManager,
    TaskManagerError,
)
from fh_agent.planner.planner_output import PlannerOutput
from fh_agent.skill_capabilities import (
    DEFAULT_RUNTIME_CAPABILITIES,
    DEFAULT_RUNTIME_SKILLS,
    SkillCapabilityContract,
)


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


def screen_point_grounding() -> GroundingResult:
    return GroundingResult(
        status="grounded",
        target=VisibleScreenPointTarget(
            target_id="point-1",
            confidence=0.9,
            evidence_ids=("target-shot-1",),
            screen_position=(120, 80),
        ),
        evidence_ids=("grounding-shot-1",),
    )


def visible_object_grounding() -> GroundingResult:
    return GroundingResult(
        status="grounded",
        target=VisibleObjectTarget(
            target_id="object-1",
            confidence=0.8,
            evidence_ids=("target-shot-2",),
            screen_position=(200, 100),
            visual_hash="visual-hash-1",
        ),
        evidence_ids=("grounding-shot-2",),
    )


def grounding_for_skill(selected_skill: str) -> GroundingResult | None:
    if selected_skill == "basic_reach_target":
        return screen_point_grounding()
    if selected_skill == "interact_visible_object":
        return visible_object_grounding()
    return None


def test_valid_planner_output_creates_valid_task_spec() -> None:
    planner_output = PlannerOutput.model_validate(valid_planner_payload())

    task = TaskManager().create_task_from_planner_output(
        planner_output,
        planner_trace_id="trace-1",
    )

    assert task.selected_skill == "continue_dialogue"
    assert task.goal == planner_output.next_goal
    assert task.target is None
    assert task.constraints["avoid_known_dangers"] is True
    assert task.success_conditions == ["new_visible_text"]
    assert task.timeout_steps == 6
    assert task.source_evidence_ids == ["shot-1", "shot-2"]
    assert task.planner_trace_id == "trace-1"
    assert {term.name for term in task.reward_profile.terms} <= ALLOWED_REWARD_TERMS


@pytest.mark.parametrize("selected_skill", DEFAULT_RUNTIME_SKILLS)
def test_default_manager_accepts_runtime_available_skill(selected_skill: str) -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = selected_skill

    task = TaskManager().create_task_from_planner_output(
        payload,
        grounding_result=grounding_for_skill(selected_skill),
    )

    assert task.selected_skill == selected_skill


@pytest.mark.parametrize("selected_skill", ["safe_reach_target", "interact_visible"])
def test_default_manager_rejects_globally_known_unavailable_skill(
    selected_skill: str,
) -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = selected_skill
    planner_output = PlannerOutput.model_validate(payload)

    with pytest.raises(
        TaskManagerError,
        match=rf"not available to this TaskManager: {selected_skill}",
    ):
        TaskManager().create_task_from_planner_output(planner_output)


def test_manager_enforces_custom_runtime_capability_subset() -> None:
    capabilities = SkillCapabilityContract(available_skills=("continue_dialogue",))
    manager = TaskManager(runtime_capabilities=capabilities)
    allowed_payload = valid_planner_payload()
    unavailable_payload = valid_planner_payload()
    unavailable_payload["selected_skill"] = "basic_reach_target"

    task = manager.create_task_from_planner_output(allowed_payload)

    assert task.selected_skill == "continue_dialogue"
    with pytest.raises(TaskManagerError, match="not available.*basic_reach_target"):
        manager.create_task_from_planner_output(unavailable_payload)


def test_capability_rejection_precedes_reward_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "safe_reach_target"

    def unexpected_reward_resolution(skill_name: str) -> None:
        pytest.fail(f"reward resolution must not run for unavailable skill: {skill_name}")

    monkeypatch.setattr(
        task_manager_module,
        "default_reward_profile_for_skill",
        unexpected_reward_resolution,
    )

    with pytest.raises(TaskManagerError, match="not available.*safe_reach_target"):
        TaskManager().create_task_from_planner_output(payload)


def test_default_manager_uses_canonical_runtime_capability_contract() -> None:
    assert TaskManager().runtime_capabilities is DEFAULT_RUNTIME_CAPABILITIES


def test_task_manager_uses_the_canonical_skill_target_requirements() -> None:
    assert task_manager_module.target_requirement_for_skill is target_requirement_for_skill
    assert target_requirement_for_skill("continue_dialogue") == "targetless"
    assert target_requirement_for_skill("basic_reach_target") == "visible_screen_point"
    assert target_requirement_for_skill("interact_visible_object") == "visible_object"


def test_continue_dialogue_rejects_unnecessary_grounded_target() -> None:
    with pytest.raises(ManagerGroundingError) as error:
        TaskManager().create_task_from_planner_output(
            valid_planner_payload(),
            grounding_result=screen_point_grounding(),
        )

    assert error.value.selected_skill == "continue_dialogue"
    assert error.value.error_code == "unexpected_grounding"
    assert error.value.evidence_ids == ("grounding-shot-1", "target-shot-1")


@pytest.mark.parametrize("selected_skill", ["basic_reach_target", "interact_visible_object"])
def test_targeted_skills_reject_missing_grounding(selected_skill: str) -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = selected_skill

    with pytest.raises(ManagerGroundingError) as error:
        TaskManager().create_task_from_planner_output(payload)

    assert error.value.selected_skill == selected_skill
    assert error.value.error_code == "missing_grounding"
    assert error.value.failure_reason is None
    assert error.value.evidence_ids == ()


def test_grounding_failure_never_produces_task_and_preserves_details() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "basic_reach_target"
    grounding = GroundingResult(
        status="grounding_failed",
        failure_reason="ambiguous_candidates",
        evidence_ids=("grounding-shot-3", "grounding-shot-4"),
    )

    with pytest.raises(ManagerGroundingError) as error:
        TaskManager().create_task_from_planner_output(
            payload,
            grounding_result=grounding,
        )

    assert error.value.selected_skill == "basic_reach_target"
    assert error.value.error_code == "grounding_failed"
    assert error.value.failure_reason == "ambiguous_candidates"
    assert error.value.evidence_ids == ("grounding-shot-3", "grounding-shot-4")


@pytest.mark.parametrize(
    ("selected_skill", "grounding"),
    [
        ("basic_reach_target", visible_object_grounding()),
        ("interact_visible_object", screen_point_grounding()),
    ],
)
def test_targeted_skills_reject_incompatible_target_type(
    selected_skill: str,
    grounding: GroundingResult,
) -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = selected_skill

    with pytest.raises(ManagerGroundingError) as error:
        TaskManager().create_task_from_planner_output(
            payload,
            grounding_result=grounding,
        )

    assert error.value.error_code == "incompatible_target_type"


def test_grounding_and_target_evidence_are_deduplicated_deterministically() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "basic_reach_target"
    grounding = GroundingResult(
        status="grounded",
        target=VisibleScreenPointTarget(
            target_id="point-1",
            confidence=0.9,
            evidence_ids=("shot-1", "target-shot-1"),
            screen_position=(120, 80),
        ),
        evidence_ids=("target-shot-1", "grounding-shot-1"),
    )

    task = TaskManager().create_task_from_planner_output(
        payload,
        grounding_result=grounding,
    )

    assert isinstance(task.target, VisibleScreenPointTarget)
    assert task.source_evidence_ids == [
        "shot-1",
        "shot-2",
        "target-shot-1",
        "grounding-shot-1",
    ]


def test_targetless_task_identity_is_deterministic() -> None:
    payload = valid_planner_payload()
    manager = TaskManager()

    first = manager.create_task_from_planner_output(payload)
    second = manager.create_task_from_planner_output(payload)

    assert first.task_id == second.task_id
    assert first.to_deterministic_json() == second.to_deterministic_json()


def test_identical_planner_intent_and_grounding_have_identical_task_identity() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "basic_reach_target"
    manager = TaskManager()

    first = manager.create_task_from_planner_output(
        payload,
        grounding_result=screen_point_grounding(),
    )
    second = manager.create_task_from_planner_output(
        payload,
        grounding_result=screen_point_grounding(),
    )

    assert first.task_id == second.task_id


def test_different_grounded_targets_have_different_task_identity() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "basic_reach_target"
    first_grounding = screen_point_grounding()
    second_grounding = GroundingResult(
        status="grounded",
        target=VisibleScreenPointTarget(
            target_id="point-2",
            confidence=0.9,
            evidence_ids=("target-shot-1",),
            screen_position=(121, 80),
        ),
        evidence_ids=("grounding-shot-1",),
    )
    manager = TaskManager()

    first = manager.create_task_from_planner_output(
        payload,
        grounding_result=first_grounding,
    )
    second = manager.create_task_from_planner_output(
        payload,
        grounding_result=second_grounding,
    )

    assert first.task_id != second.task_id


def test_target_provenance_changes_task_identity() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "basic_reach_target"
    first_grounding = screen_point_grounding()
    second_grounding = GroundingResult(
        status="grounded",
        target=VisibleScreenPointTarget(
            target_id="point-1",
            confidence=0.9,
            evidence_ids=("target-shot-2",),
            screen_position=(120, 80),
        ),
        evidence_ids=("grounding-shot-2",),
    )
    manager = TaskManager()

    first = manager.create_task_from_planner_output(
        payload,
        grounding_result=first_grounding,
    )
    second = manager.create_task_from_planner_output(
        payload,
        grounding_result=second_grounding,
    )

    assert first.source_evidence_ids != second.source_evidence_ids
    assert first.task_id != second.task_id


def test_planner_mapping_insertion_order_does_not_affect_task_identity() -> None:
    payload = valid_planner_payload()
    reordered_payload = dict(reversed(list(payload.items())))
    manager = TaskManager()

    first = manager.create_task_from_planner_output(payload)
    second = manager.create_task_from_planner_output(reordered_payload)

    assert first.task_id == second.task_id


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
    assert "SkillCatalog" not in source
    assert "fh_agent.manager.skill_catalog" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source
