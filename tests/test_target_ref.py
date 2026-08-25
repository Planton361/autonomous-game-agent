import inspect

import pytest
from pydantic import ValidationError

from fh_agent.manager import target_ref as target_ref_module
from fh_agent.manager.target_ref import (
    GroundingResult,
    VisibleObjectTarget,
    VisibleScreenPointTarget,
)


def screen_point_target() -> VisibleScreenPointTarget:
    return VisibleScreenPointTarget(
        target_id="visible-point-1",
        confidence=0.8,
        evidence_ids=("shot-1",),
        screen_position=(12, 34),
    )


def visible_object_target(*, visual_hash: str | None = None) -> VisibleObjectTarget:
    return VisibleObjectTarget(
        target_id="visible-object-1",
        confidence=0.9,
        evidence_ids=("shot-2",),
        screen_position=(56, 78),
        visual_hash=visual_hash,
    )


@pytest.mark.parametrize("target_class", [VisibleScreenPointTarget, VisibleObjectTarget])
@pytest.mark.parametrize("evidence_ids", [(), ("",)])
def test_grounded_targets_require_evidence(
    target_class: type[object],
    evidence_ids: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError):
        target_class(
            target_id="visible-target-1",
            confidence=0.5,
            evidence_ids=evidence_ids,
            screen_position=(1, 2),
        )


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
@pytest.mark.parametrize("target_class", [VisibleScreenPointTarget, VisibleObjectTarget])
def test_grounded_target_confidence_is_bounded(
    target_class: type[object],
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        target_class(
            target_id="visible-target-1",
            confidence=confidence,
            evidence_ids=("shot-1",),
            screen_position=(1, 2),
        )


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_grounded_target_accepts_inclusive_confidence_bounds(confidence: float) -> None:
    target = VisibleScreenPointTarget(
        target_id="visible-target-1",
        confidence=confidence,
        evidence_ids=("shot-1",),
        screen_position=(0, 0),
    )

    assert target.confidence == confidence


@pytest.mark.parametrize("screen_position", [(-1, 0), (0, -1)])
@pytest.mark.parametrize("target_class", [VisibleScreenPointTarget, VisibleObjectTarget])
def test_grounded_target_screen_positions_cannot_be_negative(
    target_class: type[object],
    screen_position: tuple[int, int],
) -> None:
    with pytest.raises(ValidationError):
        target_class(
            target_id="visible-target-1",
            confidence=0.5,
            evidence_ids=("shot-1",),
            screen_position=screen_position,
        )


def test_grounded_result_requires_one_target_and_no_failure_reason() -> None:
    target = screen_point_target()

    result = GroundingResult(
        status="grounded",
        target=target,
        evidence_ids=("shot-1",),
    )

    assert result.target == target
    with pytest.raises(ValidationError, match="requires a target"):
        GroundingResult(status="grounded")
    with pytest.raises(ValidationError, match="must not contain a failure_reason"):
        GroundingResult(
            status="grounded",
            target=target,
            failure_reason="insufficient_confidence",
        )


def test_grounding_failed_requires_reason_and_no_target() -> None:
    result = GroundingResult(
        status="grounding_failed",
        failure_reason="ambiguous_candidates",
        evidence_ids=("shot-1", "shot-2"),
    )

    assert result.target is None
    assert result.evidence_ids == ("shot-1", "shot-2")
    with pytest.raises(ValidationError, match="requires a failure_reason"):
        GroundingResult(status="grounding_failed")
    with pytest.raises(ValidationError, match="must not contain a target"):
        GroundingResult(
            status="grounding_failed",
            target=screen_point_target(),
            failure_reason="ambiguous_candidates",
        )


@pytest.mark.parametrize(
    "failure_reason",
    [
        "no_visible_candidate",
        "ambiguous_candidates",
        "insufficient_evidence",
        "insufficient_confidence",
        "unsupported_target_type",
        "stale_evidence",
    ],
)
def test_grounding_failure_reasons_are_supported(failure_reason: str) -> None:
    result = GroundingResult(
        status="grounding_failed",
        failure_reason=failure_reason,
    )

    assert result.failure_reason == failure_reason


@pytest.mark.parametrize("target_type", ["enemy", "door", "item", "quest_npc", "room_id"])
def test_game_semantic_target_types_are_rejected(target_type: str) -> None:
    with pytest.raises(ValidationError):
        VisibleScreenPointTarget(
            target_id="visible-target-1",
            target_type=target_type,
            confidence=0.5,
            evidence_ids=("shot-1",),
            screen_position=(1, 2),
        )


@pytest.mark.parametrize("extra_field", ["enemy", "event_id", "map_id", "room_id"])
def test_extra_hidden_and_game_specific_fields_are_rejected(extra_field: str) -> None:
    payload = {
        "target_id": "visible-target-1",
        "confidence": 0.5,
        "evidence_ids": ("shot-1",),
        "screen_position": (1, 2),
        extra_field: "forbidden",
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        VisibleObjectTarget.model_validate(payload)


def test_grounding_result_rejects_extra_hidden_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        GroundingResult.model_validate(
            {
                "status": "grounding_failed",
                "failure_reason": "insufficient_evidence",
                "map_id": 7,
            }
        )


def test_visible_object_visual_hash_is_optional_visible_identifier() -> None:
    without_hash = visible_object_target()
    with_hash = visible_object_target(visual_hash="visual-sha256-abc")

    assert without_hash.visual_hash is None
    assert with_hash.visual_hash == "visual-sha256-abc"


def test_target_contracts_are_immutable() -> None:
    target = screen_point_target()

    with pytest.raises(ValidationError):
        target.confidence = 0.1


@pytest.mark.parametrize(
    "result",
    [
        GroundingResult(status="grounded", target=screen_point_target()),
        GroundingResult(
            status="grounded",
            target=visible_object_target(visual_hash="visual-sha256-abc"),
        ),
        GroundingResult(
            status="grounding_failed",
            failure_reason="stale_evidence",
            evidence_ids=("shot-3",),
        ),
    ],
)
def test_schemas_round_trip_deterministically(result: GroundingResult) -> None:
    serialized = result.model_dump_json()

    restored = GroundingResult.model_validate_json(serialized)

    assert restored == result
    assert restored.model_dump_json() == serialized


def test_target_contract_has_no_planner_body_perception_or_adapter_dependencies() -> None:
    source = inspect.getsource(target_ref_module)

    assert "fh_agent.planner" not in source
    assert "fh_agent.body" not in source
    assert "fh_agent.perception" not in source
    assert "fh_agent.bridge" not in source
    assert "fh_agent.game" not in source
