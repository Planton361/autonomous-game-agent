import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from fh_agent.evals.controlled_live_smoke_review import ControlledLiveSmokeReviewSummary

STABILITY_REVIEW_VERSION = "1"
REQUIRED_FRAME_COUNT = 30

StabilityConclusion = Literal["passed", "failed"]


class ControlledLiveSmokeStabilityRunSummary(BaseModel):
    """One reviewed observation-only run in a stability batch."""

    model_config = ConfigDict(extra="forbid")

    review_path: Path
    run_id: str
    conclusion: str
    captured_frame_count: int
    screenshot_count: int
    evidence_count: int
    duration_seconds: float | None = None
    average_capture_interval_seconds: float | None = None
    actions_requested: int
    inputs_sent: int
    no_input_sent: bool
    stop_reason: str
    validator_passed: bool
    validation_error_count: int
    hidden_state_fields_absent: bool
    forbidden_runtime_markers_absent: bool
    planner_active: bool
    manager_active: bool
    body_active: bool
    bridge_active: bool
    learning_active: bool
    passed: bool
    failure_reasons: tuple[str, ...] = ()


class ControlledLiveSmokeStabilityReview(BaseModel):
    """Aggregate review for repeatable observation-only stability runs."""

    model_config = ConfigDict(extra="forbid")

    stability_review_version: str = STABILITY_REVIEW_VERSION
    created_at: datetime
    required_frame_count: int = REQUIRED_FRAME_COUNT
    run_count: int
    conclusion: StabilityConclusion
    runs: tuple[ControlledLiveSmokeStabilityRunSummary, ...]
    failure_reasons: tuple[str, ...] = ()

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def create_controlled_live_smoke_stability_review(
    *,
    review_paths: tuple[Path, ...],
    created_at: datetime | None = None,
) -> ControlledLiveSmokeStabilityReview:
    if not review_paths:
        msg = "at least one controlled live-smoke review path is required"
        raise ValueError(msg)

    runs = tuple(_run_summary_from_review(path) for path in review_paths)
    failure_reasons = tuple(reason for run in runs for reason in run.failure_reasons)
    conclusion: StabilityConclusion = "passed" if not failure_reasons else "failed"
    return ControlledLiveSmokeStabilityReview(
        created_at=created_at or datetime.now(UTC),
        run_count=len(runs),
        conclusion=conclusion,
        runs=runs,
        failure_reasons=failure_reasons,
    )


def write_controlled_live_smoke_stability_review(
    review: ControlledLiveSmokeStabilityReview,
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    if path.exists() and not overwrite:
        msg = f"controlled live-smoke stability review already exists: {path}"
        raise FileExistsError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(review.to_deterministic_json() + "\n", encoding="utf-8")
    return path


def read_controlled_live_smoke_review_summary(path: Path) -> ControlledLiveSmokeReviewSummary:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ControlledLiveSmokeReviewSummary.model_validate(payload)
    except FileNotFoundError as exc:
        msg = f"controlled live-smoke review file does not exist: {path}"
        raise ValueError(msg) from exc
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"invalid controlled live-smoke review file: {path}: {exc}"
        raise ValueError(msg) from exc


def _run_summary_from_review(path: Path) -> ControlledLiveSmokeStabilityRunSummary:
    review = read_controlled_live_smoke_review_summary(path)
    inputs_sent = review.input_action_counters.get("inputs_sent", 0)
    failure_reasons = _failure_reasons(review=review, inputs_sent=inputs_sent)
    return ControlledLiveSmokeStabilityRunSummary(
        review_path=path,
        run_id=review.run_id,
        conclusion=review.conclusion,
        captured_frame_count=review.captured_frame_count,
        screenshot_count=review.screenshot_count,
        evidence_count=review.evidence_count,
        duration_seconds=review.duration_seconds,
        average_capture_interval_seconds=review.average_capture_interval_seconds,
        actions_requested=review.actions_requested,
        inputs_sent=inputs_sent,
        no_input_sent=review.no_input_sent,
        stop_reason=review.stop_reason,
        validator_passed=review.validator_passed,
        validation_error_count=review.validation_error_count,
        hidden_state_fields_absent=review.hidden_state_fields_absent,
        forbidden_runtime_markers_absent=review.forbidden_runtime_markers_absent,
        planner_active=review.planner_active,
        manager_active=review.manager_active,
        body_active=review.body_active,
        bridge_active=review.bridge_active,
        learning_active=review.learning_active,
        passed=not failure_reasons,
        failure_reasons=failure_reasons,
    )


def _failure_reasons(
    *,
    review: ControlledLiveSmokeReviewSummary,
    inputs_sent: int,
) -> tuple[str, ...]:
    checks = {
        "conclusion_passed": review.conclusion == "passed",
        "captured_frame_count_30": review.captured_frame_count == REQUIRED_FRAME_COUNT,
        "screenshot_count_30": review.screenshot_count == REQUIRED_FRAME_COUNT,
        "evidence_count_30": review.evidence_count == REQUIRED_FRAME_COUNT,
        "actions_requested_zero": review.actions_requested == 0,
        "inputs_sent_zero": inputs_sent == 0,
        "no_input_sent_true": review.no_input_sent is True,
        "stop_reason_max_frames_reached": review.stop_reason == "max_frames_reached",
        "validator_passed": review.validator_passed is True,
        "validation_error_count_zero": review.validation_error_count == 0,
        "hidden_state_fields_absent": review.hidden_state_fields_absent is True,
        "forbidden_runtime_markers_absent": review.forbidden_runtime_markers_absent is True,
        "planner_inactive": review.planner_active is False,
        "manager_inactive": review.manager_active is False,
        "body_inactive": review.body_active is False,
        "bridge_inactive": review.bridge_active is False,
        "learning_inactive": review.learning_active is False,
    }
    return tuple(name for name, passed in checks.items() if not passed)
