import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from fh_agent.evals.live_run_manifest import (
    FixedResolutionSnapshot,
    ManifestMode,
    RepoMetadata,
    create_live_run_manifest,
    read_preflight_report,
    write_live_run_manifest,
)
from fh_agent.evals.live_smoke_plan import (
    create_live_smoke_plan,
    read_live_run_manifest,
    write_live_smoke_plan,
)
from fh_agent.evals.live_smoke_report import (
    create_noop_live_smoke_report,
    read_live_smoke_plan,
    write_live_smoke_report,
)

PIPELINE_VERSION = "1"

StageName = Literal["preflight", "manifest", "smoke_plan", "smoke_report", "summary"]
StageStatus = Literal["succeeded", "failed", "skipped"]


class LiveAuditPipelineStage(BaseModel):
    """Status for one audit-artifact pipeline stage."""

    model_config = ConfigDict(extra="forbid")

    name: StageName
    status: StageStatus
    artifact_path: Path | None = None
    message: str


class LiveAuditPipelineResult(BaseModel):
    """Summary for the non-executing live audit artifact pipeline."""

    model_config = ConfigDict(extra="forbid")

    pipeline_version: str = PIPELINE_VERSION
    run_id: str
    created_at: datetime
    execution_enabled: bool = False
    official_run_allowed: bool
    mode: ManifestMode
    preflight_report_path: Path
    manifest_path: Path
    smoke_plan_path: Path
    smoke_report_path: Path
    summary_path: Path
    stages: tuple[LiveAuditPipelineStage, ...]
    validation_errors: tuple[str, ...] = ()

    @model_validator(mode="after")
    def execution_must_stay_disabled(self) -> "LiveAuditPipelineResult":
        if self.execution_enabled:
            msg = "live audit pipeline must never enable execution"
            raise ValueError(msg)
        return self

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def run_live_audit_pipeline(
    *,
    run_id: str,
    preflight_report_path: Path,
    mode: ManifestMode,
    runs_dir: Path = Path("runs"),
    screenshots_dir: Path = Path("screenshots"),
    reports_dir: Path | None = None,
    expected_window_title: str | None = None,
    expected_resolution: FixedResolutionSnapshot | None = None,
    overwrite: bool = False,
    created_at: datetime | None = None,
    repo_metadata: RepoMetadata | None = None,
) -> LiveAuditPipelineResult:
    """Build the audit chain from existing JSON artifact functions only."""

    timestamp = created_at or datetime.now(UTC)
    paths = _pipeline_paths(
        run_id=run_id,
        runs_dir=runs_dir,
        reports_dir=reports_dir,
    )
    stages: list[LiveAuditPipelineStage] = []
    validation_errors: list[str] = []
    official_run_allowed = False

    try:
        preflight = read_preflight_report(preflight_report_path)
        stages.append(
            LiveAuditPipelineStage(
                name="preflight",
                status="succeeded",
                artifact_path=preflight_report_path,
                message="preflight report loaded",
            )
        )
    except ValueError as exc:
        validation_errors.append(str(exc))
        stages.append(
            LiveAuditPipelineStage(
                name="preflight",
                status="failed",
                artifact_path=preflight_report_path,
                message=str(exc),
            )
        )
        _append_skipped_after(stages, failed_stage="preflight", paths=paths)
        return _result(
            run_id=run_id,
            created_at=timestamp,
            mode=mode,
            preflight_report_path=preflight_report_path,
            paths=paths,
            stages=stages,
            validation_errors=validation_errors,
            official_run_allowed=False,
        )

    try:
        manifest = create_live_run_manifest(
            run_id=run_id,
            mode=mode,
            preflight_result=preflight,
            runs_dir=runs_dir,
            screenshots_dir=screenshots_dir,
            reports_dir=paths["reports_dir"],
            manifest_path=paths["manifest"],
            expected_window_title=expected_window_title,
            expected_resolution=expected_resolution,
            created_at=timestamp,
            repo_metadata=repo_metadata,
        )
        write_live_run_manifest(manifest, overwrite=overwrite)
        loaded_manifest = read_live_run_manifest(paths["manifest"])
        stages.append(
            LiveAuditPipelineStage(
                name="manifest",
                status="succeeded",
                artifact_path=paths["manifest"],
                message="manifest written and validated",
            )
        )
    except (FileExistsError, ValueError) as exc:
        validation_errors.append(str(exc))
        stages.append(
            LiveAuditPipelineStage(
                name="manifest",
                status="failed",
                artifact_path=paths["manifest"],
                message=str(exc),
            )
        )
        _append_skipped_after(stages, failed_stage="manifest", paths=paths)
        return _result(
            run_id=run_id,
            created_at=timestamp,
            mode=mode,
            preflight_report_path=preflight_report_path,
            paths=paths,
            stages=stages,
            validation_errors=validation_errors,
            official_run_allowed=False,
        )

    try:
        plan = create_live_smoke_plan(
            manifest=loaded_manifest,
            source_manifest_path=paths["manifest"],
            source_preflight_path=preflight_report_path,
            smoke_plan_path=paths["smoke_plan"],
            final_report_path=paths["smoke_report"],
            created_at=timestamp,
        )
        write_live_smoke_plan(plan, overwrite=overwrite)
        loaded_plan = read_live_smoke_plan(paths["smoke_plan"])
        stages.append(
            LiveAuditPipelineStage(
                name="smoke_plan",
                status="succeeded",
                artifact_path=paths["smoke_plan"],
                message="smoke plan written and validated",
            )
        )
    except (FileExistsError, ValueError) as exc:
        validation_errors.append(str(exc))
        stages.append(
            LiveAuditPipelineStage(
                name="smoke_plan",
                status="failed",
                artifact_path=paths["smoke_plan"],
                message=str(exc),
            )
        )
        _append_skipped_after(stages, failed_stage="smoke_plan", paths=paths)
        return _result(
            run_id=run_id,
            created_at=timestamp,
            mode=mode,
            preflight_report_path=preflight_report_path,
            paths=paths,
            stages=stages,
            validation_errors=validation_errors,
            official_run_allowed=False,
        )

    try:
        report = create_noop_live_smoke_report(
            plan=loaded_plan,
            source_plan_path=paths["smoke_plan"],
            created_at=timestamp,
        )
        write_live_smoke_report(report, overwrite=overwrite)
        stages.append(
            LiveAuditPipelineStage(
                name="smoke_report",
                status="succeeded",
                artifact_path=paths["smoke_report"],
                message="no-op smoke report written",
            )
        )
        official_run_allowed = (
            preflight.ok
            and loaded_manifest.official_run_allowed
            and loaded_plan.official_run_allowed
            and report.official_run_allowed
        )
        validation_errors.extend(loaded_plan.validation_errors)
        validation_errors.extend(report.blocked_reasons)
    except (FileExistsError, ValueError) as exc:
        validation_errors.append(str(exc))
        stages.append(
            LiveAuditPipelineStage(
                name="smoke_report",
                status="failed",
                artifact_path=paths["smoke_report"],
                message=str(exc),
            )
        )

    return _result(
        run_id=run_id,
        created_at=timestamp,
        mode=mode,
        preflight_report_path=preflight_report_path,
        paths=paths,
        stages=stages,
        validation_errors=validation_errors,
        official_run_allowed=official_run_allowed and not validation_errors,
    )


def write_live_audit_pipeline_result(
    result: LiveAuditPipelineResult,
    *,
    overwrite: bool = False,
) -> Path:
    """Persist the pipeline summary, refusing to clobber by default."""

    if result.summary_path.exists() and not overwrite:
        msg = f"pipeline summary already exists: {result.summary_path}"
        raise FileExistsError(msg)
    result.summary_path.parent.mkdir(parents=True, exist_ok=True)
    result.summary_path.write_text(result.to_deterministic_json() + "\n", encoding="utf-8")
    return result.summary_path


def _pipeline_paths(
    *,
    run_id: str,
    runs_dir: Path,
    reports_dir: Path | None,
) -> dict[str, Path]:
    run_dir = runs_dir / run_id
    resolved_reports_dir = reports_dir or run_dir / "reports"
    return {
        "reports_dir": resolved_reports_dir,
        "manifest": resolved_reports_dir / "live_run_manifest.json",
        "smoke_plan": resolved_reports_dir / "live_smoke_plan.json",
        "smoke_report": resolved_reports_dir / "live_smoke_report.json",
        "summary": resolved_reports_dir / "live_audit_pipeline.json",
    }


def _append_skipped_after(
    stages: list[LiveAuditPipelineStage],
    *,
    failed_stage: StageName,
    paths: dict[str, Path],
) -> None:
    ordered: tuple[StageName, ...] = (
        "preflight",
        "manifest",
        "smoke_plan",
        "smoke_report",
    )
    artifact_paths = {
        "manifest": paths["manifest"],
        "smoke_plan": paths["smoke_plan"],
        "smoke_report": paths["smoke_report"],
    }
    should_skip = False
    for stage_name in ordered:
        if should_skip:
            stages.append(
                LiveAuditPipelineStage(
                    name=stage_name,
                    status="skipped",
                    artifact_path=artifact_paths.get(stage_name),
                    message=f"skipped after {failed_stage} failed",
                )
            )
        if stage_name == failed_stage:
            should_skip = True


def _result(
    *,
    run_id: str,
    created_at: datetime,
    mode: ManifestMode,
    preflight_report_path: Path,
    paths: dict[str, Path],
    stages: list[LiveAuditPipelineStage],
    validation_errors: list[str],
    official_run_allowed: bool,
) -> LiveAuditPipelineResult:
    return LiveAuditPipelineResult(
        run_id=run_id,
        created_at=created_at,
        official_run_allowed=official_run_allowed,
        mode=mode,
        preflight_report_path=preflight_report_path,
        manifest_path=paths["manifest"],
        smoke_plan_path=paths["smoke_plan"],
        smoke_report_path=paths["smoke_report"],
        summary_path=paths["summary"],
        stages=tuple(stages),
        validation_errors=tuple(dict.fromkeys(validation_errors)),
    )
