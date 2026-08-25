import inspect

import pytest
from pydantic import ValidationError

from fh_agent.manager import grounding as grounding_module
from fh_agent.manager.grounding import (
    BoundedObservationGroundingService,
    GroundingPolicy,
    GroundingRequest,
    GroundingService,
)
from fh_agent.manager.target_ref import VisibleObjectTarget, VisibleScreenPointTarget
from fh_agent.observation.schemas import Observation, VisibleSprite


def request(
    *,
    selected_skill: str = "interact_visible_object",
    semantic_goal: str = "Interact with the visible object.",
    evidence_scope_ids: tuple[str, ...] = ("shot-1",),
) -> GroundingRequest:
    return GroundingRequest(
        selected_skill=selected_skill,
        semantic_goal=semantic_goal,
        evidence_scope_ids=evidence_scope_ids,
    )


def sprite(
    *,
    screen_position: tuple[int, int] = (120, 80),
    visual_hash: str | None = "visible-hash-1",
    confidence: float | None = 0.9,
    evidence_id: str | None = "sprite-shot-1",
) -> VisibleSprite:
    return VisibleSprite(
        screen_position=screen_position,
        visual_hash=visual_hash,
        confidence=confidence,
        evidence_id=evidence_id,
    )


def observation(
    *,
    sprites: list[VisibleSprite] | None = None,
    evidence_ids: list[str] | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="field",
        visible_sprites=[] if sprites is None else sprites,
        evidence_ids=["shot-1"] if evidence_ids is None else evidence_ids,
    )


def test_one_visible_object_grounds_interact_visible_object() -> None:
    result = BoundedObservationGroundingService().ground(
        request(),
        observation(sprites=[sprite()]),
    )

    assert result.status == "grounded"
    assert isinstance(result.target, VisibleObjectTarget)
    assert result.target.screen_position == (120, 80)
    assert result.target.visual_hash == "visible-hash-1"
    assert result.evidence_ids == ("shot-1", "sprite-shot-1")


def test_visible_object_projects_to_screen_point_for_basic_reach_target() -> None:
    result = BoundedObservationGroundingService().ground(
        request(selected_skill="basic_reach_target"),
        observation(sprites=[sprite()]),
    )

    assert result.status == "grounded"
    assert isinstance(result.target, VisibleScreenPointTarget)
    assert result.target.screen_position == (120, 80)


def test_zero_candidates_fail_deterministically() -> None:
    service = BoundedObservationGroundingService()

    first = service.ground(request(), observation())
    second = service.ground(request(), observation())

    assert first == second
    assert first.status == "grounding_failed"
    assert first.failure_reason == "no_visible_candidate"
    assert first.evidence_ids == ("shot-1",)


def test_multiple_confident_candidates_are_ambiguous() -> None:
    result = BoundedObservationGroundingService().ground(
        request(),
        observation(
            sprites=[
                sprite(evidence_id="sprite-shot-1"),
                sprite(screen_position=(160, 80), evidence_id="sprite-shot-2"),
            ]
        ),
    )

    assert result.status == "grounding_failed"
    assert result.failure_reason == "ambiguous_candidates"
    assert result.evidence_ids == ("shot-1", "sprite-shot-1", "sprite-shot-2")


def test_below_threshold_candidates_fail_with_insufficient_confidence() -> None:
    service = BoundedObservationGroundingService(policy=GroundingPolicy(min_confidence=0.8))

    result = service.ground(
        request(),
        observation(sprites=[sprite(confidence=0.79)]),
    )

    assert result.status == "grounding_failed"
    assert result.failure_reason == "insufficient_confidence"


def test_missing_candidate_confidence_is_handled_conservatively() -> None:
    result = BoundedObservationGroundingService().ground(
        request(),
        observation(sprites=[sprite(confidence=None)]),
    )

    assert result.status == "grounding_failed"
    assert result.failure_reason == "insufficient_confidence"


def test_stale_evidence_scope_fails_and_preserves_relevant_evidence() -> None:
    result = BoundedObservationGroundingService().ground(
        request(evidence_scope_ids=("earlier-shot",)),
        observation(sprites=[sprite()], evidence_ids=["shot-1"]),
    )

    assert result.status == "grounding_failed"
    assert result.failure_reason == "stale_evidence"
    assert result.evidence_ids == ("earlier-shot", "shot-1", "sprite-shot-1")


def test_missing_usable_observation_evidence_fails() -> None:
    result = BoundedObservationGroundingService().ground(
        request(evidence_scope_ids=("shot-1",)),
        observation(sprites=[sprite(evidence_id=None)], evidence_ids=[]),
    )

    assert result.status == "grounding_failed"
    assert result.failure_reason == "insufficient_evidence"
    assert result.evidence_ids == ("shot-1",)


def test_targetless_skills_are_not_grounded() -> None:
    result = BoundedObservationGroundingService().ground(
        request(selected_skill="continue_dialogue"),
        observation(sprites=[sprite()]),
    )

    assert result.status == "grounding_failed"
    assert result.failure_reason == "unsupported_target_type"
    assert result.target is None


def test_semantic_goal_is_not_used_to_invent_or_select_a_target() -> None:
    service = BoundedObservationGroundingService()
    visible_observation = observation(sprites=[sprite()])

    first = service.ground(
        request(semantic_goal="Reach the visible exit."),
        visible_observation,
    )
    second = service.ground(
        request(semantic_goal="Avoid the enemy and use the nearby item."),
        visible_observation,
    )

    assert first == second


def test_deterministic_inputs_produce_deterministic_target_identity() -> None:
    service: GroundingService = BoundedObservationGroundingService()
    grounded_request = request()
    visible_observation = observation(sprites=[sprite()])

    first = service.ground(grounded_request, visible_observation)
    second = service.ground(grounded_request, visible_observation)

    assert first == second
    assert first.target is not None
    assert first.target.target_id == second.target.target_id


def test_changed_visible_evidence_changes_target_identity() -> None:
    service = BoundedObservationGroundingService()
    first = service.ground(
        request(evidence_scope_ids=("shot-1",)),
        observation(sprites=[sprite(evidence_id="sprite-shot-1")], evidence_ids=["shot-1"]),
    )
    second = service.ground(
        request(evidence_scope_ids=("shot-2",)),
        observation(sprites=[sprite(evidence_id="sprite-shot-2")], evidence_ids=["shot-2"]),
    )

    assert first.target is not None
    assert second.target is not None
    assert first.target.target_id != second.target.target_id


def test_request_and_policy_are_strict_and_immutable() -> None:
    with pytest.raises(ValidationError):
        GroundingRequest.model_validate(
            {
                "selected_skill": "continue_dialogue",
                "semantic_goal": "Continue visible dialogue.",
                "evidence_scope_ids": (),
                "hidden_target": "map_id",
            }
        )
    with pytest.raises(ValidationError):
        GroundingPolicy(min_confidence=1.1)

    request_value = request()
    with pytest.raises(ValidationError):
        request_value.semantic_goal = "Changed"


def test_grounding_module_has_no_forbidden_dependencies_or_game_specific_state() -> None:
    source = inspect.getsource(grounding_module)

    assert "fh_agent.body" not in source
    assert "fh_agent.planner" not in source
    assert "fh_agent.perception" not in source
    assert "fh_agent.bridge" not in source
    assert "fh_agent.game" not in source
    assert "map" + "_id" not in source
    assert "event" + "_id" not in source
