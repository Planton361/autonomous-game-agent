from datetime import UTC, datetime

from fh_agent.evals.reference_spatial_producer import (
    SyntheticReferenceSpatialProducer,
    SyntheticReferenceSpatialProducerConfig,
)
from fh_agent.evals.spatial_perception_benchmark import run_spatial_perception_benchmark
from fh_agent.evals.spatial_perception_dataset import (
    SpatialPerceptionDataset,
    SpatialPerceptionFrameAnnotation,
    SpatialPerceptionSequence,
)
from fh_agent.evals.spatial_perception_metrics import SpatialPerceptionEvaluationConfig
from fh_agent.observation.schemas import VisibleSprite
from fh_agent.perception.screen_capture import ScreenFrame
from fh_agent.perception.spatial_producer import SpatialPerceptionOutput

PLAYER = (10, 20, 30)
SPRITE = (40, 50, 60)
BACKGROUND = (0, 0, 0)


def frame(
    markers: dict[tuple[int, int], tuple[int, int, int]],
    *,
    width: int = 12,
    height: int = 4,
) -> ScreenFrame:
    pixels = [BACKGROUND] * (width * height)
    for (x, y), color in markers.items():
        pixels[y * width + x] = color
    return ScreenFrame(
        width=width,
        height=height,
        rgb=bytes(channel for pixel in pixels for channel in pixel),
        captured_at=datetime(2026, 8, 24, tzinfo=UTC),
    )


def producer() -> SyntheticReferenceSpatialProducer:
    return SyntheticReferenceSpatialProducer(
        SyntheticReferenceSpatialProducerConfig(player_marker=PLAYER, sprite_marker=SPRITE)
    )


def dataset(*annotations: SpatialPerceptionFrameAnnotation) -> SpatialPerceptionDataset:
    return SpatialPerceptionDataset(
        dataset_version="synthetic-reference-v1",
        sequences=(SpatialPerceptionSequence(sequence_id="sequence-1", frames=annotations),),
    )


def annotation(
    frame_id: str,
    *,
    sprites: tuple[tuple[int, int], ...] = (),
    player: tuple[int, int] | None = None,
    status: str = "usable",
) -> SpatialPerceptionFrameAnnotation:
    return SpatialPerceptionFrameAnnotation(
        frame_id=frame_id,
        evidence_id=f"evidence-{frame_id}",
        status=status,
        player_screen_position=player,
        visible_sprite_positions=sprites,
    )


def test_perfect_synthetic_predictions_produce_a_complete_perfect_report() -> None:
    report = run_spatial_perception_benchmark(
        dataset(annotation("frame-1", sprites=((2, 1),), player=(1, 1))),
        {"frame-1": frame({(1, 1): PLAYER, (2, 1): SPRITE})},
        producer(),
        config=SpatialPerceptionEvaluationConfig(matching_tolerance_px=2.0),
    )

    assert report.producer_name == "synthetic_reference_rgb_marker"
    assert report.producer_version == "1"
    assert report.evaluated_frame_count == 1
    assert report.sprite_precision == 1.0
    assert report.sprite_recall == 1.0
    assert report.sprite_f1 == 1.0
    assert report.sprite_false_positives == 0
    assert report.sprite_false_negatives == 0
    assert report.mean_matched_sprite_position_error == 0.0
    assert report.player_detection_rate == 1.0
    assert report.mean_player_position_error == 0.0
    assert report.match_radius_px == 2.0


def test_missing_and_outside_tolerance_detections_lower_recall() -> None:
    report = run_spatial_perception_benchmark(
        dataset(
            annotation("missing", sprites=((1, 1),)),
            annotation("outside", sprites=((0, 0),)),
        ),
        {
            "missing": frame({}),
            "outside": frame({(8, 0): SPRITE}),
        },
        producer(),
        config=SpatialPerceptionEvaluationConfig(matching_tolerance_px=2.0),
    )

    assert report.sprite_recall == 0.0
    assert report.sprite_false_negatives == 2
    assert report.sprite_false_positives == 1


def test_false_positive_sprite_lowers_precision() -> None:
    report = run_spatial_perception_benchmark(
        dataset(annotation("frame-1")),
        {"frame-1": frame({(2, 1): SPRITE})},
        producer(),
    )

    assert report.sprite_false_positives == 1
    assert report.sprite_precision == 0.0


def test_confidence_threshold_is_forwarded_to_the_canonical_metrics() -> None:
    class LowConfidenceProducer:
        def predict(
            self, captured_frame: ScreenFrame, *, evidence_id: str
        ) -> SpatialPerceptionOutput:
            return SpatialPerceptionOutput(
                producer_name="low-confidence-fixture",
                producer_version="1",
                evidence_id=evidence_id,
                visible_sprites=(
                    VisibleSprite(screen_position=(1, 1), confidence=0.4, evidence_id=evidence_id),
                ),
            )

    report = run_spatial_perception_benchmark(
        dataset(annotation("frame-1", sprites=((1, 1),))),
        {"frame-1": frame({})},
        LowConfidenceProducer(),
        config=SpatialPerceptionEvaluationConfig(min_confidence=0.5),
    )

    assert report.min_confidence == 0.5
    assert report.sprite_recall == 0.0
    assert report.sprite_false_negatives == 1


def test_excluded_and_uncertain_annotations_are_not_scored() -> None:
    report = run_spatial_perception_benchmark(
        dataset(
            annotation("exclude", sprites=((1, 1),), status="exclude"),
            annotation("uncertain", sprites=((1, 1),), status="uncertain"),
            annotation("usable", sprites=((1, 1),)),
        ),
        {
            "exclude": frame({}),
            "uncertain": frame({}),
            "usable": frame({(1, 1): SPRITE}),
        },
        producer(),
    )

    assert report.evaluated_frame_count == 1
    assert report.excluded_frame_count == 1
    assert report.uncertain_frame_count == 1
    assert report.skipped_frame_count == 2
    assert report.sprite_precision == 1.0


def test_benchmark_report_is_deterministic() -> None:
    benchmark = dataset(
        annotation("frame-2", sprites=((2, 1),)),
        annotation("frame-1", sprites=((1, 1),)),
    )
    frames = {
        "frame-2": frame({(2, 1): SPRITE}),
        "frame-1": frame({(1, 1): SPRITE}),
    }

    first = run_spatial_perception_benchmark(benchmark, frames, producer())
    second = run_spatial_perception_benchmark(
        benchmark,
        dict(reversed(list(frames.items()))),
        producer(),
    )

    assert first == second
