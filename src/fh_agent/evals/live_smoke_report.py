import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from fh_agent.evals.live_run_manifest import ManifestMode, NoSpoilerPolicySnapshot
from fh_agent.evals.live_smoke_plan import (
    LiveSmokeExpectedOutputs,
    LiveSmokeRunPlan,
    LiveSmokeStopCondition,
)

REPORT_VERSION = "1"

ReadinessSeverity = Literal["info", "warning", "blocker"]
ExecutionStatus = Literal["not_executed"]


class LiveSmokeReadinessGap(BaseModel):
    """A transparent readiness note for a no-op smoke report."""

    model_config = ConfigDict(extra="forbid")

    name: str
    severity: ReadinessSeverity
    message: str


class LiveSmokeRunReport(BaseModel):
    """No-op report shape for a future live smoke run report."""

    model_config = ConfigDict(extra="forbid")

    report_version: str = REPORT_VERSION
    run_id: str
    created_at: datetime
    execution_status: ExecutionStatus = "not_executed"
    execution_enabled: bool = False
    official_run_allowed: bool
    source_plan_path: Path
    mode: ManifestMode
    readiness_gaps: tuple[LiveSmokeReadinessGap, ...]
    blocked_reasons: tuple[str, ...]
    stop_conditions: tuple[LiveSmokeStopCondition, ...]
    expected_outputs: LiveSmokeExpectedOutputs
    observed_outputs: dict[str, None]
    no_spoiler_policy_snapshot: NoSpoilerPolicySnapshot

    @model_validator(mode="after")
    def enforce_noop_status(self) -> "LiveSmokeRunReport":
        if self.execution_status != "not_executed":
            msg = "no-op smoke reports must use execution_status='not_executed'"
            raise ValueError(msg)
        if self.execution_enabled:
            msg = "no-op smoke reports must never enable execution"
            raise ValueError(msg)
        if self.observed_outputs:
            msg = "no-op smoke reports must not claim observed runtime outputs"
            raise ValueError(msg)
        return self

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def read_live_smoke_plan(path: Path) -> LiveSmokeRunPlan:
    """Load and validate a dry LiveSmokeRunPlan JSON file."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return LiveSmokeRunPlan.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"invalid live-smoke plan: {path}: {exc}"
        raise ValueError(msg) from exc


def create_noop_live_smoke_report(
    *,
    plan: LiveSmokeRunPlan,
    source_plan_path: Path,
    created_at: datetime | None = None,
) -> LiveSmokeRunReport:
    """Create a no-op report without inventing runtime observations or events."""

    readiness_gaps = _readiness_gaps_from_plan(plan)
    blocked_reasons = tuple(
        gap.name for gap in readiness_gaps if gap.severity in {"warning", "blocker"}
    )
    return LiveSmokeRunReport(
        run_id=plan.run_id,
        created_at=created_at or datetime.now(UTC),
        official_run_allowed=plan.official_run_allowed,
        source_plan_path=source_plan_path,
        mode=plan.mode,
        readiness_gaps=tuple(readiness_gaps),
        blocked_reasons=blocked_reasons,
        stop_conditions=plan.stop_conditions,
        expected_outputs=plan.expected_outputs,
        observed_outputs={},
        no_spoiler_policy_snapshot=plan.no_spoiler_policy_snapshot,
    )


def write_live_smoke_report(report: LiveSmokeRunReport, *, overwrite: bool = False) -> Path:
    """Persist a no-op smoke report, refusing to clobber by default."""

    report_path = report.expected_outputs.final_report_path
    if report_path.exists() and not overwrite:
        msg = f"smoke report already exists: {report_path}"
        raise FileExistsError(msg)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.to_deterministic_json() + "\n", encoding="utf-8")
    return report_path


def _readiness_gaps_from_plan(plan: LiveSmokeRunPlan) -> list[LiveSmokeReadinessGap]:
    gaps = [
        LiveSmokeReadinessGap(
            name="execution_disabled",
            severity="info",
            message="no live execution was performed; this is a no-op smoke report",
        )
    ]
    for validation_error in plan.validation_errors:
        gaps.append(
            LiveSmokeReadinessGap(
                name=validation_error,
                severity="blocker",
                message=f"plan validation error blocks official execution: {validation_error}",
            )
        )
    if not plan.official_run_allowed:
        gaps.append(
            LiveSmokeReadinessGap(
                name="official_run_not_allowed",
                severity="blocker",
                message="source plan does not allow an official live run",
            )
        )
    return gaps
