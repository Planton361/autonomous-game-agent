"""Deterministic point-matching metrics for offline spatial-perception evaluation."""

from collections.abc import Mapping, Sequence
from math import hypot

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.evals.spatial_perception_dataset import (
    SpatialPerceptionDataset,
    SpatialPerceptionFrameAnnotation,
)
from fh_agent.perception.spatial_producer import SpatialPerceptionOutput


class SpatialPerceptionEvaluationConfig(BaseModel):
    """Explicit point-matching and prediction-filter configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    matching_tolerance_px: float = Field(default=5.0, ge=0.0)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


DEFAULT_SPATIAL_PERCEPTION_EVALUATION_CONFIG = SpatialPerceptionEvaluationConfig()


class SpatialPerceptionMetrics(BaseModel):
    """Aggregate point-detection metrics over usable annotated frames only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluated_frame_count: int = Field(ge=0)
    skipped_frame_count: int = Field(ge=0)
    sprite_true_positives: int = Field(ge=0)
    sprite_false_positives: int = Field(ge=0)
    sprite_false_negatives: int = Field(ge=0)
    sprite_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    sprite_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    sprite_f1: float | None = Field(default=None, ge=0.0, le=1.0)
    mean_matched_sprite_position_error: float | None = Field(default=None, ge=0.0)
    player_ground_truth_count: int = Field(ge=0)
    player_detected_count: int = Field(ge=0)
    player_false_positives: int = Field(ge=0)
    player_detection_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    mean_player_position_error: float | None = Field(default=None, ge=0.0)


def evaluate_spatial_perception(
    dataset: SpatialPerceptionDataset,
    predictions: Mapping[str, SpatialPerceptionOutput],
    *,
    config: SpatialPerceptionEvaluationConfig | None = None,
) -> SpatialPerceptionMetrics:
    """Evaluate confidence-filtered point predictions with deterministic one-to-one matching."""

    active_config = config or DEFAULT_SPATIAL_PERCEPTION_EVALUATION_CONFIG
    annotations = _annotations_by_frame_id(dataset)
    unknown_prediction_ids = sorted(set(predictions) - set(annotations))
    if unknown_prediction_ids:
        joined = ", ".join(unknown_prediction_ids)
        msg = f"predictions contain unknown frame_ids: {joined}"
        raise ValueError(msg)

    evaluated_frame_count = 0
    skipped_frame_count = 0
    sprite_true_positives = 0
    sprite_false_positives = 0
    sprite_false_negatives = 0
    sprite_errors: list[float] = []
    player_ground_truth_count = 0
    player_detected_count = 0
    player_false_positives = 0
    player_errors: list[float] = []

    for frame_id in sorted(annotations):
        annotation = annotations[frame_id]
        if annotation.status != "usable":
            skipped_frame_count += 1
            continue
        evaluated_frame_count += 1
        output = predictions.get(frame_id)
        if output is not None and output.evidence_id != annotation.evidence_id:
            msg = f"prediction evidence_id does not match annotation for frame_id: {frame_id}"
            raise ValueError(msg)

        predicted_sprite_positions = _filtered_sprite_positions(
            output, active_config.min_confidence
        )
        matches, unmatched_prediction_count, unmatched_target_count = _match_points(
            predicted_sprite_positions,
            annotation.visible_sprite_positions,
            tolerance=active_config.matching_tolerance_px,
        )
        sprite_true_positives += len(matches)
        sprite_false_positives += unmatched_prediction_count
        sprite_false_negatives += unmatched_target_count
        sprite_errors.extend(matches)

        player_prediction = _filtered_player_position(output, active_config.min_confidence)
        if annotation.player_screen_position is not None:
            player_ground_truth_count += 1
            if player_prediction is not None:
                player_error = _distance(player_prediction, annotation.player_screen_position)
                if player_error <= active_config.matching_tolerance_px:
                    player_detected_count += 1
                    player_errors.append(player_error)
        elif player_prediction is not None:
            player_false_positives += 1

    sprite_precision = _ratio(sprite_true_positives, sprite_true_positives + sprite_false_positives)
    sprite_recall = _ratio(sprite_true_positives, sprite_true_positives + sprite_false_negatives)
    sprite_f1 = _f1(sprite_precision, sprite_recall)
    return SpatialPerceptionMetrics(
        evaluated_frame_count=evaluated_frame_count,
        skipped_frame_count=skipped_frame_count,
        sprite_true_positives=sprite_true_positives,
        sprite_false_positives=sprite_false_positives,
        sprite_false_negatives=sprite_false_negatives,
        sprite_precision=sprite_precision,
        sprite_recall=sprite_recall,
        sprite_f1=sprite_f1,
        mean_matched_sprite_position_error=_mean(sprite_errors),
        player_ground_truth_count=player_ground_truth_count,
        player_detected_count=player_detected_count,
        player_false_positives=player_false_positives,
        player_detection_rate=_ratio(player_detected_count, player_ground_truth_count),
        mean_player_position_error=_mean(player_errors),
    )


def _annotations_by_frame_id(
    dataset: SpatialPerceptionDataset,
) -> dict[str, SpatialPerceptionFrameAnnotation]:
    return {frame.frame_id: frame for sequence in dataset.sequences for frame in sequence.frames}


def _filtered_sprite_positions(
    output: SpatialPerceptionOutput | None,
    min_confidence: float,
) -> tuple[tuple[int, int], ...]:
    if output is None:
        return ()
    return tuple(
        sprite.screen_position
        for sprite in output.visible_sprites
        if sprite.confidence is not None and sprite.confidence >= min_confidence
    )


def _filtered_player_position(
    output: SpatialPerceptionOutput | None,
    min_confidence: float,
) -> tuple[int, int] | None:
    if output is None or output.player_prediction is None:
        return None
    if output.player_prediction.confidence < min_confidence:
        return None
    return output.player_prediction.screen_position


def _match_points(
    predicted_positions: Sequence[tuple[int, int]],
    target_positions: Sequence[tuple[int, int]],
    *,
    tolerance: float,
) -> tuple[list[float], int, int]:
    """Find a deterministic maximum-cardinality one-to-one point matching."""

    ordered_prediction_indices = sorted(
        range(len(predicted_positions)),
        key=lambda index: (predicted_positions[index], index),
    )
    candidate_target_indices = {
        prediction_index: sorted(
            (
                target_index
                for target_index, target in enumerate(target_positions)
                if _distance(predicted_positions[prediction_index], target) <= tolerance
            ),
            key=lambda target_index: (
                _distance(predicted_positions[prediction_index], target_positions[target_index]),
                target_positions[target_index],
                target_index,
            ),
        )
        for prediction_index in ordered_prediction_indices
    }
    matched_targets: dict[int, int] = {}

    def assign_prediction(prediction_index: int, seen_targets: set[int]) -> bool:
        for target_index in candidate_target_indices[prediction_index]:
            if target_index in seen_targets:
                continue
            seen_targets.add(target_index)
            current_prediction = matched_targets.get(target_index)
            if current_prediction is None or assign_prediction(current_prediction, seen_targets):
                matched_targets[target_index] = prediction_index
                return True
        return False

    for prediction_index in ordered_prediction_indices:
        assign_prediction(prediction_index, set())

    errors = [
        _distance(predicted_positions[prediction_index], target_positions[target_index])
        for target_index, prediction_index in sorted(matched_targets.items())
    ]
    return (
        errors,
        len(predicted_positions) - len(matched_targets),
        len(target_positions) - len(matched_targets),
    )


def _distance(left: tuple[int, int], right: tuple[int, int]) -> float:
    return hypot(left[0] - right[0], left[1] - right[1])


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
