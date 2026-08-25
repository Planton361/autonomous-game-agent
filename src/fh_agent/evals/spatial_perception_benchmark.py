"""Offline benchmark runner for canonical spatial-perception producers."""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.evals.spatial_perception_dataset import SpatialPerceptionDataset
from fh_agent.evals.spatial_perception_metrics import (
    DEFAULT_SPATIAL_PERCEPTION_EVALUATION_CONFIG,
    SpatialPerceptionEvaluationConfig,
    evaluate_spatial_perception,
)
from fh_agent.perception.screen_capture import ScreenFrame
from fh_agent.perception.spatial_producer import SpatialPerceptionProducer


class SpatialPerceptionBenchmarkReport(BaseModel):
    """Reproducible aggregate result of an offline spatial-perception benchmark."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    producer_name: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    evaluated_frame_count: int = Field(ge=0)
    excluded_frame_count: int = Field(ge=0)
    uncertain_frame_count: int = Field(ge=0)
    skipped_frame_count: int = Field(ge=0)
    sprite_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    sprite_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    sprite_f1: float | None = Field(default=None, ge=0.0, le=1.0)
    sprite_false_positives: int = Field(ge=0)
    sprite_false_negatives: int = Field(ge=0)
    mean_matched_sprite_position_error: float | None = Field(default=None, ge=0.0)
    player_detection_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    mean_player_position_error: float | None = Field(default=None, ge=0.0)
    match_radius_px: float = Field(ge=0.0)
    min_confidence: float = Field(ge=0.0, le=1.0)


def run_spatial_perception_benchmark(
    dataset: SpatialPerceptionDataset,
    frames: Mapping[str, ScreenFrame],
    producer: SpatialPerceptionProducer,
    *,
    config: SpatialPerceptionEvaluationConfig | None = None,
) -> SpatialPerceptionBenchmarkReport:
    """Run one injected producer and delegate scoring to the canonical metrics."""

    active_config = config or DEFAULT_SPATIAL_PERCEPTION_EVALUATION_CONFIG
    annotations = {
        annotation.frame_id: annotation
        for sequence in dataset.sequences
        for annotation in sequence.frames
    }
    if not annotations:
        msg = "benchmark dataset must contain at least one frame annotation"
        raise ValueError(msg)

    _validate_frame_coverage(annotations, frames)
    predictions = {
        frame_id: producer.predict(frames[frame_id], evidence_id=annotation.evidence_id)
        for frame_id, annotation in sorted(annotations.items())
    }
    producer_metadata = {
        (output.producer_name, output.producer_version) for output in predictions.values()
    }
    if len(producer_metadata) != 1:
        msg = "producer metadata must be consistent across benchmark frames"
        raise ValueError(msg)

    metrics = evaluate_spatial_perception(dataset, predictions, config=active_config)
    producer_name, producer_version = next(iter(producer_metadata))
    return SpatialPerceptionBenchmarkReport(
        producer_name=producer_name,
        producer_version=producer_version,
        evaluated_frame_count=metrics.evaluated_frame_count,
        excluded_frame_count=sum(
            annotation.status == "exclude" for annotation in annotations.values()
        ),
        uncertain_frame_count=sum(
            annotation.status == "uncertain" for annotation in annotations.values()
        ),
        skipped_frame_count=metrics.skipped_frame_count,
        sprite_precision=metrics.sprite_precision,
        sprite_recall=metrics.sprite_recall,
        sprite_f1=metrics.sprite_f1,
        sprite_false_positives=metrics.sprite_false_positives,
        sprite_false_negatives=metrics.sprite_false_negatives,
        mean_matched_sprite_position_error=metrics.mean_matched_sprite_position_error,
        player_detection_rate=metrics.player_detection_rate,
        mean_player_position_error=metrics.mean_player_position_error,
        match_radius_px=active_config.matching_tolerance_px,
        min_confidence=active_config.min_confidence,
    )


def _validate_frame_coverage(
    annotations: Mapping[str, object],
    frames: Mapping[str, ScreenFrame],
) -> None:
    annotation_ids = set(annotations)
    frame_ids = set(frames)
    missing_frame_ids = sorted(annotation_ids - frame_ids)
    unexpected_frame_ids = sorted(frame_ids - annotation_ids)
    if missing_frame_ids or unexpected_frame_ids:
        details = []
        if missing_frame_ids:
            details.append(f"missing frames: {', '.join(missing_frame_ids)}")
        if unexpected_frame_ids:
            details.append(f"unexpected frames: {', '.join(unexpected_frame_ids)}")
        msg = "; ".join(details)
        raise ValueError(msg)
