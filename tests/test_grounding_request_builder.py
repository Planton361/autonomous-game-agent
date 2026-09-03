import inspect

import fh_agent.manager.grounding_request_builder as builder_module
from fh_agent.manager.grounding import BoundedObservationGroundingService, GroundingRequest
from fh_agent.manager.grounding_request_builder import build_grounding_request
from fh_agent.observation.schemas import Observation, VisibleSprite
from fh_agent.planner.planner_output import PlannerOutput


def planner_output(
    *,
    selected_skill: str = "basic_reach_target",
    next_goal: str = "Reach the visible location.",
    fact_evidence_ids: list[str] | None = None,
    memory_evidence_ids: list[str] | None = None,
) -> PlannerOutput:
    return PlannerOutput.model_validate(
        {
            "current_belief_state": [
                {
                    "kind": "fact",
                    "claim": "A prior visible fact is available.",
                    "evidence_ids": fact_evidence_ids or ["shot-prior"],
                }
            ],
            "next_goal": next_goal,
            "selected_skill": selected_skill,
            "success_condition": ["visible_change"],
            "memory_updates_requested": (
                []
                if memory_evidence_ids is None
                else [{"claim": "Remember visible context.", "evidence_ids": memory_evidence_ids}]
            ),
        }
    )


def observation(
    *,
    evidence_ids: list[str] | None = None,
    screenshot_id: str | None = "shot-descriptive",
    sprites: list[VisibleSprite] | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="field",
        screenshot_id=screenshot_id,
        evidence_ids=[] if evidence_ids is None else evidence_ids,
        visible_sprites=[] if sprites is None else sprites,
    )


def test_targetless_continue_dialogue_returns_none() -> None:
    assert (
        build_grounding_request(
            planner_output(selected_skill="continue_dialogue"),
            observation(evidence_ids=["shot-1"]),
        )
        is None
    )


def test_target_requiring_skills_preserve_selected_skill_and_semantic_goal() -> None:
    for selected_skill in ("basic_reach_target", "interact_visible_object"):
        output = planner_output(selected_skill=selected_skill, next_goal="Use the visible target.")

        request = build_grounding_request(output, observation(evidence_ids=["shot-1"]))

        assert isinstance(request, GroundingRequest)
        assert request.selected_skill == selected_skill
        assert request.semantic_goal == output.next_goal


def test_request_scope_uses_only_current_evidence_in_order_without_duplicates() -> None:
    request = build_grounding_request(
        planner_output(
            fact_evidence_ids=["shot-prior", "shot-current"],
            memory_evidence_ids=["memory-prior"],
        ),
        observation(evidence_ids=["shot-current", "", "shot-next", "shot-current"]),
    )

    assert request is not None
    assert request.evidence_scope_ids == ("shot-current", "shot-next")


def test_screenshot_and_candidate_evidence_do_not_expand_request_scope() -> None:
    request = build_grounding_request(
        planner_output(selected_skill="interact_visible_object"),
        observation(
            evidence_ids=[],
            screenshot_id="shot-descriptive-only",
            sprites=[
                VisibleSprite(
                    screen_position=(10, 20),
                    confidence=0.9,
                    evidence_id="sprite-shot-1",
                )
            ],
        ),
    )

    assert request is not None
    assert request.evidence_scope_ids == ()


def test_changed_current_evidence_changes_scope_without_mutating_inputs() -> None:
    output = planner_output()
    first_observation = observation(evidence_ids=["shot-1"])
    second_observation = observation(evidence_ids=["shot-2"])
    output_before = output.model_dump()
    first_before = first_observation.model_dump()

    first = build_grounding_request(output, first_observation)
    second = build_grounding_request(output, second_observation)

    assert first is not None and second is not None
    assert first.evidence_scope_ids == ("shot-1",)
    assert second.evidence_scope_ids == ("shot-2",)
    assert output.model_dump() == output_before
    assert first_observation.model_dump() == first_before


def test_derived_request_keeps_candidate_evidence_for_grounding_service_to_add() -> None:
    output = planner_output(
        selected_skill="interact_visible_object",
        next_goal="Interact with the visible object.",
    )
    current_observation = observation(
        evidence_ids=["shot-1"],
        sprites=[
            VisibleSprite(
                screen_position=(120, 80),
                visual_hash="visible-hash-1",
                confidence=0.9,
                evidence_id="sprite-shot-1",
            )
        ],
    )

    request = build_grounding_request(output, current_observation)
    assert request is not None
    result = BoundedObservationGroundingService().ground(request, current_observation)

    assert request.evidence_scope_ids == ("shot-1",)
    assert result.status == "grounded"
    assert result.target is not None
    assert result.evidence_ids == ("shot-1", "sprite-shot-1")
    assert result.target.evidence_ids == ("shot-1", "sprite-shot-1")


def test_empty_current_evidence_reaches_grounding_service_insufficient_evidence() -> None:
    output = planner_output(selected_skill="interact_visible_object")
    current_observation = observation(
        evidence_ids=[],
        screenshot_id="shot-descriptive-only",
        sprites=[VisibleSprite(screen_position=(120, 80), confidence=0.9)],
    )

    request = build_grounding_request(output, current_observation)
    assert request is not None
    result = BoundedObservationGroundingService().ground(request, current_observation)

    assert request.evidence_scope_ids == ()
    assert result.status == "grounding_failed"
    assert result.failure_reason == "insufficient_evidence"


def test_builder_has_only_narrow_composition_dependencies() -> None:
    source = inspect.getsource(builder_module)

    for forbidden in (
        "Cortex",
        "LLMClient",
        "CortexTaskSubmitter",
        "ManagerOrchestrator",
        "TaskManager",
        "ManagerTaskExecutor",
        "SkillRunner",
        "InputExecutor",
        "Verifier",
        "reward",
        "fh_agent.bridge",
        "fh_agent.game",
        "fh_agent.memory",
    ):
        assert forbidden not in source
