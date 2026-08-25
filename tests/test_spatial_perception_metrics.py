import pytest

from fh_agent.evals.spatial_perception_dataset import (
    SpatialPerceptionDataset,
    SpatialPerceptionFrameAnnotation,
    SpatialPerceptionSequence,
)
from fh_agent.evals.spatial_perception_metrics import (
    SpatialPerceptionEvaluationConfig,
    evaluate_spatial_perception,
)
from fh_agent.observation.schemas import VisibleSprite
from fh_agent.perception.spatial_producer import (
    PlayerScreenPositionPrediction,
    SpatialPerceptionOutput,
)


def annotation(
    frame_id: str,
    *,
    sprite_positions: tuple[tuple[int, int], ...] = (),
    player_position: tuple[int, int] | None = None,
    status: str = "usable",
) -> SpatialPerceptionFrameAnnotation:
    return SpatialPerceptionFrameAnnotation(
        frame_id=frame_id,
        evidence_id=f"evidence-{frame_id}",
        status=status,
        player_screen_position=player_position,
        visible_sprite_positions=sprite_positions,
    )


def dataset(*frames: SpatialPerceptionFrameAnnotation) -> SpatialPerceptionDataset:
    return SpatialPerceptionDataset(
        dataset_version="synthetic-v1",
        sequences=(SpatialPerceptionSequence(sequence_id="sequence-1", frames=frames),),
    )


def prediction(
    frame_id: str,
    *,
    sprite_predictions: tuple[tuple[tuple[int, int], float], ...] = (),
    player_prediction: tuple[tuple[int, int], float] | None = None,
) -> SpatialPerceptionOutput:
    evidence_id = f"evidence-{frame_id}"
    return SpatialPerceptionOutput(
        producer_name="synthetic-spatial-producer",
        producer_version="0.1",
        evidence_id=evidence_id,
        player_prediction=(
            PlayerScreenPositionPrediction(
                screen_position=player_prediction[0],
                confidence=player_prediction[1],
                evidence_id=evidence_id,
            )
            if player_prediction is not None
            else None
        ),
        visible_sprites=tuple(
            VisibleSprite(
                screen_position=position,
                confidence=confidence,
                evidence_id=evidence_id,
            )
            for position, confidence in sprite_predictions
        ),
    )


def config(
    *, tolerance: float = 5.0, min_confidence: float = 0.0
) -> SpatialPerceptionEvaluationConfig:
    return SpatialPerceptionEvaluationConfig(
        matching_tolerance_px=tolerance,
        min_confidence=min_confidence,
    )


def test_perfect_predictions_report_perfect_sprite_and_player_metrics() -> None:
    metrics = evaluate_spatial_perception(
        dataset(annotation("frame-1", sprite_positions=((0, 0), (10, 0)), player_position=(5, 5))),
        {
            "frame-1": prediction(
                "frame-1",
                sprite_predictions=(((0, 0), 0.9), ((10, 0), 0.8)),
                player_prediction=((5, 5), 0.9),
            )
        },
        config=config(),
    )

    assert metrics.sprite_true_positives == 2
    assert metrics.sprite_false_positives == 0
    assert metrics.sprite_false_negatives == 0
    assert metrics.sprite_precision == 1.0
    assert metrics.sprite_recall == 1.0
    assert metrics.sprite_f1 == 1.0
    assert metrics.mean_matched_sprite_position_error == 0.0
    assert metrics.player_detection_rate == 1.0
    assert metrics.mean_player_position_error == 0.0


def test_missing_predictions_report_false_negatives_and_undefined_precision() -> None:
    metrics = evaluate_spatial_perception(
        dataset(annotation("frame-1", sprite_positions=((0, 0),))),
        {},
        config=config(),
    )

    assert metrics.sprite_true_positives == 0
    assert metrics.sprite_false_negatives == 1
    assert metrics.sprite_precision is None
    assert metrics.sprite_recall == 0.0
    assert metrics.sprite_f1 is None


def test_false_positive_predictions_are_reported() -> None:
    metrics = evaluate_spatial_perception(
        dataset(annotation("frame-1", sprite_positions=((0, 0),))),
        {"frame-1": prediction("frame-1", sprite_predictions=(((0, 0), 0.9), ((20, 0), 0.9)))},
        config=config(),
    )

    assert metrics.sprite_true_positives == 1
    assert metrics.sprite_false_positives == 1
    assert metrics.sprite_false_negatives == 0
    assert metrics.sprite_precision == 0.5
    assert metrics.sprite_recall == 1.0
    assert metrics.sprite_f1 == pytest.approx(2 / 3)


def test_tolerance_boundary_counts_as_a_match_and_reports_position_error() -> None:
    metrics = evaluate_spatial_perception(
        dataset(annotation("frame-1", sprite_positions=((0, 0),))),
        {"frame-1": prediction("frame-1", sprite_predictions=(((3, 4), 0.9),))},
        config=config(tolerance=5.0),
    )

    assert metrics.sprite_true_positives == 1
    assert metrics.mean_matched_sprite_position_error == 5.0


def test_one_prediction_cannot_match_multiple_ground_truth_points() -> None:
    metrics = evaluate_spatial_perception(
        dataset(annotation("frame-1", sprite_positions=((0, 0), (10, 0)))),
        {"frame-1": prediction("frame-1", sprite_predictions=(((5, 0), 0.9),))},
        config=config(tolerance=5.0),
    )

    assert metrics.sprite_true_positives == 1
    assert metrics.sprite_false_negatives == 1
    assert metrics.sprite_false_positives == 0


def test_multiple_object_matching_is_deterministic_and_input_order_independent() -> None:
    first_dataset = dataset(annotation("frame-2", sprite_positions=((10, 0), (0, 0))))
    second_dataset = dataset(annotation("frame-2", sprite_positions=((0, 0), (10, 0))))
    first_predictions = {
        "frame-2": prediction(
            "frame-2",
            sprite_predictions=(((9, 0), 0.8), ((1, 0), 0.8)),
        )
    }
    second_predictions = {
        "frame-2": prediction(
            "frame-2",
            sprite_predictions=(((1, 0), 0.8), ((9, 0), 0.8)),
        )
    }

    first = evaluate_spatial_perception(first_dataset, first_predictions, config=config())
    second = evaluate_spatial_perception(second_dataset, second_predictions, config=config())

    assert first == second
    assert first.sprite_true_positives == 2
    assert first.mean_matched_sprite_position_error == 1.0


def test_player_position_error_uses_the_same_explicit_tolerance() -> None:
    metrics = evaluate_spatial_perception(
        dataset(annotation("frame-1", player_position=(0, 0))),
        {"frame-1": prediction("frame-1", player_prediction=((3, 4), 0.9))},
        config=config(tolerance=5.0),
    )

    assert metrics.player_detection_rate == 1.0
    assert metrics.mean_player_position_error == 5.0


def test_uncertain_and_excluded_annotations_are_not_scored() -> None:
    metrics = evaluate_spatial_perception(
        dataset(
            annotation("exclude", sprite_positions=((0, 0),), status="exclude"),
            annotation("uncertain", sprite_positions=((0, 0),), status="uncertain"),
            annotation("usable", sprite_positions=((0, 0),)),
        ),
        {
            "exclude": prediction("exclude", sprite_predictions=(((20, 0), 0.9),)),
            "uncertain": prediction("uncertain", sprite_predictions=(((20, 0), 0.9),)),
            "usable": prediction("usable", sprite_predictions=(((0, 0), 0.9),)),
        },
        config=config(),
    )

    assert metrics.evaluated_frame_count == 1
    assert metrics.skipped_frame_count == 2
    assert metrics.sprite_true_positives == 1
    assert metrics.sprite_false_positives == 0


def test_confidence_threshold_filters_sprite_and_player_predictions() -> None:
    metrics = evaluate_spatial_perception(
        dataset(annotation("frame-1", sprite_positions=((0, 0),), player_position=(5, 5))),
        {
            "frame-1": prediction(
                "frame-1",
                sprite_predictions=(((0, 0), 0.4),),
                player_prediction=((5, 5), 0.4),
            )
        },
        config=config(min_confidence=0.5),
    )

    assert metrics.sprite_true_positives == 0
    assert metrics.sprite_false_negatives == 1
    assert metrics.player_detection_rate == 0.0


def test_evaluation_is_deterministic_independent_of_prediction_mapping_order() -> None:
    benchmark = dataset(
        annotation("frame-2", sprite_positions=((10, 0),)),
        annotation("frame-1", sprite_positions=((0, 0),)),
    )
    first_predictions = {
        "frame-1": prediction("frame-1", sprite_predictions=(((0, 0), 0.9),)),
        "frame-2": prediction("frame-2", sprite_predictions=(((10, 0), 0.9),)),
    }
    second_predictions = dict(reversed(list(first_predictions.items())))

    first = evaluate_spatial_perception(benchmark, first_predictions, config=config())
    second = evaluate_spatial_perception(benchmark, second_predictions, config=config())

    assert first == second
