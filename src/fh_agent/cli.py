import json
from pathlib import Path
from subprocess import run
from typing import Annotated, Literal, cast

import click
import typer
from pydantic import BaseModel, ValidationError
from rich.console import Console

from fh_agent import __version__
from fh_agent.evals.controlled_live_runtime_adapters import build_controlled_runtime_adapters
from fh_agent.evals.controlled_live_smoke_review import (
    create_controlled_live_smoke_review_summary,
    record_controlled_live_smoke_manual_visual_review,
    write_controlled_live_smoke_manual_visual_review,
    write_controlled_live_smoke_review_summary,
)
from fh_agent.evals.controlled_live_smoke_runner import (
    read_live_audit_pipeline_result,
    run_controlled_live_smoke,
)
from fh_agent.evals.controlled_live_smoke_stability_review import (
    create_controlled_live_smoke_stability_review,
    write_controlled_live_smoke_stability_review,
)
from fh_agent.evals.controlled_live_smoke_validator import (
    default_validation_report_path,
    validate_controlled_live_smoke_artifacts,
    write_controlled_live_smoke_validation_report,
)
from fh_agent.evals.live_audit_pipeline import (
    run_live_audit_pipeline,
    write_live_audit_pipeline_result,
)
from fh_agent.evals.live_run_manifest import (
    FixedResolutionSnapshot,
    create_live_run_manifest,
    read_preflight_report,
    write_live_run_manifest,
)
from fh_agent.evals.live_run_preflight import (
    FixedResolution,
    LiveRunPreflightConfig,
    run_live_preflight,
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
from fh_agent.evals.spatial_annotation_review import (
    SpatialAnnotationWorkflow,
    assess_spatial_corpus_readiness,
    create_annotation_review,
    freeze_spatial_corpus,
    record_spatial_annotation,
)
from fh_agent.evals.spatial_corpus_assembler import (
    SpatialCorpusSequenceSource,
    assemble_spatial_perception_corpus,
)
from fh_agent.evals.spatial_perception_corpus import validate_spatial_perception_corpus_files
from fh_agent.evals.spatial_perception_dataset import SpatialPerceptionFrameAnnotation

app = typer.Typer(
    add_completion=False,
    help="Fear & Hunger no-spoiler agent tooling.",
)
console = Console()
DEFAULT_SCREENSHOTS_DIR = Path("screenshots")
DEFAULT_RUNS_DIR = Path("runs")


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show package version and exit.",
    ),
) -> None:
    """Run fh-agent commands."""
    if version:
        console.print(f"fh-agent {__version__}")
        raise typer.Exit()


@app.command()
def capture(
    run_id: Annotated[str, typer.Option("--run-id", help="Run identifier for output paths.")],
    frames: Annotated[
        int,
        typer.Option("--frames", min=0, help="Number of dummy frames to capture."),
    ] = 1,
    screenshots_dir: Annotated[
        Path,
        typer.Option("--screenshots-dir", help="Directory where screenshot evidence is stored."),
    ] = DEFAULT_SCREENSHOTS_DIR,
    runs_dir: Annotated[
        Path,
        typer.Option("--runs-dir", help="Directory where run event logs are stored."),
    ] = DEFAULT_RUNS_DIR,
    allow_existing_run: Annotated[
        bool,
        typer.Option("--allow-existing-run", help="Append to an existing run instead of failing."),
    ] = False,
) -> None:
    """Capture dummy frames and log screenshot evidence."""
    from fh_agent.perception.capture_session import CaptureSession, CaptureSessionConfig
    from fh_agent.perception.screen_capture import DummyScreenCapture

    session = CaptureSession(
        CaptureSessionConfig(
            run_id=run_id,
            frame_count=frames,
            screenshots_dir=screenshots_dir,
            runs_dir=runs_dir,
            allow_existing_run=allow_existing_run,
        ),
        capture=DummyScreenCapture(),
    )
    result = session.run()
    console.print(f"run_id: {result.run_id}")
    console.print(f"frames_saved: {result.frames_saved}")
    console.print(f"event_log_path: {result.event_log_path}")
    console.print(f"screenshot_dir: {result.screenshot_dir}")


@app.command("parse-frame")
def parse_frame(
    path: Annotated[Path, typer.Argument(help="Saved PPM screenshot to parse.")],
    run_id: Annotated[str, typer.Option("--run-id", help="Run identifier for the observation.")],
    evidence_id: Annotated[
        str | None,
        typer.Option("--evidence-id", help="Evidence identifier. Defaults to the filename stem."),
    ] = None,
    ui_hint: Annotated[
        str | None,
        typer.Option(
            "--ui-hint",
            help="Optional visible UI hint: field, dialogue, menu, combat, death, unknown.",
        ),
    ] = None,
) -> None:
    """Parse one saved offline frame into Observation JSON."""
    from fh_agent.observation.schemas import UIState
    from fh_agent.perception.offline_processor import observation_to_json, process_saved_frame

    allowed_hints = {"field", "dialogue", "menu", "combat", "death", "unknown"}
    if ui_hint is not None and ui_hint not in allowed_hints:
        msg = f"ui_hint must be one of: {', '.join(sorted(allowed_hints))}"
        raise typer.BadParameter(msg)

    observation = process_saved_frame(
        path,
        run_id=run_id,
        evidence_id=evidence_id,
        ui_hint=cast(UIState | None, ui_hint),
    )
    console.print(observation_to_json(observation))


@app.command("spatial-corpus-assemble")
def spatial_corpus_assemble(
    corpus_root: Annotated[
        Path,
        typer.Option(
            "--corpus-root", help="Root containing explicit manually captured PPM sequences."
        ),
    ],
    corpus_id: Annotated[str, typer.Option("--corpus-id", help="Versioned corpus identifier.")],
    schema_version: Annotated[str, typer.Option("--schema-version", help="Corpus schema version.")],
    corpus_version: Annotated[
        str, typer.Option("--corpus-version", help="Corpus content version.")
    ],
    annotation_dataset_version: Annotated[
        str,
        typer.Option("--annotation-dataset-version", help="Initial annotation dataset version."),
    ],
    sequence: Annotated[
        list[str],
        typer.Option(
            "--sequence",
            help="Repeat SEQUENCE_ID:RELATIVE_DIRECTORY:SPLIT for each explicit source sequence.",
        ),
    ],
    output: Annotated[Path, typer.Option("--output", help="Workflow JSON output path.")],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing workflow JSON output."),
    ] = False,
) -> None:
    """Assemble existing PPM sequences into a point-only offline corpus workflow."""

    try:
        sources = tuple(_parse_spatial_sequence_source(value) for value in sequence)
        manifest = assemble_spatial_perception_corpus(
            corpus_root,
            corpus_id=corpus_id,
            schema_version=schema_version,
            corpus_version=corpus_version,
            annotation_dataset_version=annotation_dataset_version,
            sequence_sources=sources,
        )
        path = _write_spatial_annotation_workflow(
            SpatialAnnotationWorkflow(manifest=manifest),
            output,
            overwrite=overwrite,
        )
    except (FileExistsError, OSError, ValidationError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(path))


@app.command("spatial-corpus-annotate")
def spatial_corpus_annotate(
    workflow: Annotated[
        Path, typer.Option("--workflow", help="Existing corpus workflow JSON path.")
    ],
    frame_id: Annotated[
        str, typer.Option("--frame-id", help="Existing frame identifier to revise.")
    ],
    status: Annotated[
        str,
        typer.Option("--status", help="Annotation status: usable, uncertain, or exclude."),
    ],
    player: Annotated[
        str | None,
        typer.Option("--player", help="Optional visible player point as X,Y."),
    ] = None,
    sprite: Annotated[
        list[str] | None,
        typer.Option("--sprite", help="Visible sprite point as X,Y. Repeat for each point."),
    ] = None,
    output: Annotated[
        Path, typer.Option("--output", help="Revised workflow JSON output path.")
    ] = Path("spatial_annotation_workflow.json"),
    overwrite_annotation: Annotated[
        bool,
        typer.Option(
            "--overwrite-annotation", help="Required explicit annotation revision action."
        ),
    ] = False,
    overwrite_output: Annotated[
        bool,
        typer.Option("--overwrite-output", help="Replace an existing workflow JSON output."),
    ] = False,
) -> None:
    """Record one explicit point-only annotation revision for an existing corpus frame."""

    if status not in {"usable", "uncertain", "exclude"}:
        raise typer.BadParameter("--status must be usable, uncertain, or exclude")
    try:
        current_workflow = _read_spatial_annotation_workflow(workflow)
        current_annotation = _spatial_annotation_by_frame_id(current_workflow, frame_id)
        annotation = SpatialPerceptionFrameAnnotation(
            frame_id=frame_id,
            evidence_id=current_annotation.evidence_id,
            status=status,
            player_screen_position=_parse_spatial_coordinate(player)
            if player is not None
            else None,
            visible_sprite_positions=tuple(
                _parse_spatial_coordinate(value) for value in sprite or ()
            ),
        )
        revised_workflow = record_spatial_annotation(
            current_workflow,
            annotation,
            overwrite=overwrite_annotation,
        )
        path = _write_spatial_annotation_workflow(
            revised_workflow,
            output,
            overwrite=overwrite_output,
        )
    except (FileExistsError, OSError, ValidationError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(path))


@app.command("spatial-corpus-review")
def spatial_corpus_review(
    workflow: Annotated[
        Path, typer.Option("--workflow", help="Existing corpus workflow JSON path.")
    ],
    frame_id: Annotated[str, typer.Option("--frame-id", help="Frame identifier to review.")],
    status: Annotated[
        str,
        typer.Option("--status", help="Review status: passed or needs_revision."),
    ],
    output: Annotated[Path, typer.Option("--output", help="Reviewed workflow JSON output path.")],
    reviewer: Annotated[
        str | None,
        typer.Option("--reviewer", help="Optional reviewer identifier."),
    ] = None,
    notes: Annotated[str | None, typer.Option("--notes", help="Optional review notes.")] = None,
    overwrite_output: Annotated[
        bool,
        typer.Option("--overwrite-output", help="Replace an existing workflow JSON output."),
    ] = False,
) -> None:
    """Append a review bound to the current annotation fingerprint."""

    if status not in {"passed", "needs_revision"}:
        raise typer.BadParameter("--status must be passed or needs_revision")
    try:
        reviewed_workflow = create_annotation_review(
            _read_spatial_annotation_workflow(workflow),
            frame_id=frame_id,
            status=cast(Literal["passed", "needs_revision"], status),
            reviewer_id=reviewer,
            notes=notes,
        )
        path = _write_spatial_annotation_workflow(
            reviewed_workflow,
            output,
            overwrite=overwrite_output,
        )
    except (FileExistsError, KeyError, OSError, ValidationError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(path))


@app.command("spatial-corpus-validate")
def spatial_corpus_validate(
    workflow: Annotated[
        Path, typer.Option("--workflow", help="Existing corpus workflow JSON path.")
    ],
    corpus_root: Annotated[
        Path,
        typer.Option(
            "--corpus-root", help="Root containing the externally stored PPM corpus files."
        ),
    ],
) -> None:
    """Validate existing corpus file and split integrity without inspecting image semantics."""

    try:
        result = validate_spatial_perception_corpus_files(
            _read_spatial_annotation_workflow(workflow).manifest,
            corpus_root,
        )
    except (OSError, ValidationError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(_to_deterministic_json(result))
    if not result.valid:
        raise typer.Exit(code=1)


@app.command("spatial-corpus-readiness")
def spatial_corpus_readiness(
    workflow: Annotated[
        Path, typer.Option("--workflow", help="Existing corpus workflow JSON path.")
    ],
    corpus_root: Annotated[
        Path,
        typer.Option(
            "--corpus-root", help="Root containing the externally stored PPM corpus files."
        ),
    ],
) -> None:
    """Report deterministic annotation, review, integrity, and freeze readiness counts."""

    try:
        current_workflow = _read_spatial_annotation_workflow(workflow)
        integrity_result = validate_spatial_perception_corpus_files(
            current_workflow.manifest,
            corpus_root,
        )
        summary = assess_spatial_corpus_readiness(current_workflow, integrity_result)
    except (OSError, ValidationError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(_to_deterministic_json(summary))


@app.command("spatial-corpus-freeze")
def spatial_corpus_freeze(
    workflow: Annotated[
        Path, typer.Option("--workflow", help="Existing corpus workflow JSON path.")
    ],
    corpus_root: Annotated[
        Path,
        typer.Option(
            "--corpus-root", help="Root containing the externally stored PPM corpus files."
        ),
    ],
    output: Annotated[Path, typer.Option("--output", help="Frozen workflow JSON output path.")],
    overwrite_output: Annotated[
        bool,
        typer.Option("--overwrite-output", help="Replace an existing workflow JSON output."),
    ] = False,
) -> None:
    """Freeze one fully reviewed and integrity-valid corpus version."""

    try:
        current_workflow = _read_spatial_annotation_workflow(workflow)
        integrity_result = validate_spatial_perception_corpus_files(
            current_workflow.manifest,
            corpus_root,
        )
        readiness = assess_spatial_corpus_readiness(current_workflow, integrity_result)
        if not readiness.freeze_ready:
            reasons = ", ".join(readiness.blocked_reasons)
            raise ValueError(f"corpus is not ready to freeze: {reasons}")
        frozen_workflow = freeze_spatial_corpus(current_workflow, integrity_result)
        path = _write_spatial_annotation_workflow(
            frozen_workflow,
            output,
            overwrite=overwrite_output,
        )
    except (FileExistsError, OSError, ValidationError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(path))


@app.command("live-preflight")
def live_preflight(
    run_id: Annotated[
        str | None,
        typer.Option("--run-id", help="Run identifier for preflight output paths."),
    ] = None,
    runs_dir: Annotated[
        Path,
        typer.Option("--runs-dir", help="Directory where future run logs will be stored."),
    ] = DEFAULT_RUNS_DIR,
    evidence_dir: Annotated[
        Path,
        typer.Option("--evidence-dir", help="Directory where future evidence will be stored."),
    ] = DEFAULT_SCREENSHOTS_DIR,
    width: Annotated[
        int,
        typer.Option("--width", min=1, help="Required fixed live-run window width."),
    ] = 1280,
    height: Annotated[
        int,
        typer.Option("--height", min=1, help="Required fixed live-run window height."),
    ] = 720,
    no_spoiler_mode: Annotated[
        bool,
        typer.Option(help="Require no-spoiler mode."),
    ] = True,
    emergency_stop_required: Annotated[
        bool,
        typer.Option(help="Require emergency stop configuration."),
    ] = True,
    focus_guard_required: Annotated[
        bool,
        typer.Option(help="Require focus guard configuration."),
    ] = True,
    live_inputs_enabled: Annotated[
        bool,
        typer.Option(help="Must remain false for preflight."),
    ] = False,
    bridge_hidden_state_enabled: Annotated[
        bool,
        typer.Option(help="Must remain false for official no-spoiler runs."),
    ] = False,
    debug_oracle_enabled: Annotated[
        bool,
        typer.Option(help="Must remain false for official no-spoiler runs."),
    ] = False,
) -> None:
    """Check controlled live-run prerequisites without starting live automation."""
    result = run_live_preflight(
        LiveRunPreflightConfig(
            runs_dir=runs_dir,
            evidence_dir=evidence_dir,
            run_id=run_id,
            no_spoiler_mode=no_spoiler_mode,
            emergency_stop_required=emergency_stop_required,
            focus_guard_required=focus_guard_required,
            fixed_resolution=FixedResolution(width=width, height=height),
            live_inputs_enabled=live_inputs_enabled,
            bridge_hidden_state_enabled=bridge_hidden_state_enabled,
            debug_oracle_enabled=debug_oracle_enabled,
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if not result.ok:
        raise typer.Exit(code=1)


@app.command("live-manifest")
def live_manifest(
    run_id: Annotated[str, typer.Option("--run-id", help="Run identifier for the manifest.")],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Manifest mode: official_screen_only, debug_visible_bridge, or dry_run.",
        ),
    ],
    preflight_report: Annotated[
        Path,
        typer.Option("--preflight-report", help="JSON report from live-preflight."),
    ],
    runs_dir: Annotated[
        Path,
        typer.Option("--runs-dir", help="Directory where future run logs will be stored."),
    ] = DEFAULT_RUNS_DIR,
    screenshots_dir: Annotated[
        Path,
        typer.Option(
            "--screenshots-dir",
            help="Directory where future screenshots will be stored.",
        ),
    ] = DEFAULT_SCREENSHOTS_DIR,
    reports_dir: Annotated[
        Path | None,
        typer.Option("--reports-dir", help="Directory where the manifest report will be stored."),
    ] = None,
    manifest_path: Annotated[
        Path | None,
        typer.Option("--manifest-path", help="Explicit manifest JSON path."),
    ] = None,
    expected_window_title: Annotated[
        str | None,
        typer.Option("--expected-window-title", help="Optional expected game window title."),
    ] = None,
    width: Annotated[
        int | None,
        typer.Option("--width", min=1, help="Optional expected fixed window width."),
    ] = None,
    height: Annotated[
        int | None,
        typer.Option("--height", min=1, help="Optional expected fixed window height."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing manifest file."),
    ] = False,
) -> None:
    """Write a live-run audit manifest without starting live automation."""
    allowed_modes = {"official_screen_only", "debug_visible_bridge", "dry_run"}
    if mode not in allowed_modes:
        msg = f"mode must be one of: {', '.join(sorted(allowed_modes))}"
        raise typer.BadParameter(msg)
    if (width is None) != (height is None):
        raise typer.BadParameter("width and height must be provided together")

    try:
        preflight_result = read_preflight_report(preflight_report)
        expected_resolution = (
            FixedResolutionSnapshot(width=width, height=height)
            if width is not None and height is not None
            else None
        )
        manifest = create_live_run_manifest(
            run_id=run_id,
            mode=mode,  # type: ignore[arg-type]
            preflight_result=preflight_result,
            runs_dir=runs_dir,
            screenshots_dir=screenshots_dir,
            reports_dir=reports_dir,
            manifest_path=manifest_path,
            expected_window_title=expected_window_title,
            expected_resolution=expected_resolution,
        )
        path = write_live_run_manifest(manifest, overwrite=overwrite)
    except (FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(str(path))


@app.command("live-smoke-plan")
def live_smoke_plan(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", help="Live-run manifest JSON path."),
    ],
    smoke_plan_path: Annotated[
        Path | None,
        typer.Option("--smoke-plan-path", help="Explicit smoke plan JSON path."),
    ] = None,
    final_report_path: Annotated[
        Path | None,
        typer.Option("--final-report-path", help="Expected final smoke report path."),
    ] = None,
    source_preflight_path: Annotated[
        Path | None,
        typer.Option("--source-preflight-path", help="Optional source preflight report path."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing smoke plan file."),
    ] = False,
) -> None:
    """Write a dry live-smoke audit plan without starting live automation."""
    try:
        live_manifest_model = read_live_run_manifest(manifest)
        plan = create_live_smoke_plan(
            manifest=live_manifest_model,
            source_manifest_path=manifest,
            source_preflight_path=source_preflight_path,
            smoke_plan_path=smoke_plan_path,
            final_report_path=final_report_path,
        )
        path = write_live_smoke_plan(plan, overwrite=overwrite)
    except (FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(str(path))


@app.command("live-smoke-report")
def live_smoke_report(
    plan: Annotated[
        Path,
        typer.Option("--plan", help="Dry live-smoke plan JSON path."),
    ],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing smoke report file."),
    ] = False,
) -> None:
    """Write a no-op live-smoke report without starting live automation."""
    try:
        smoke_plan = read_live_smoke_plan(plan)
        report = create_noop_live_smoke_report(
            plan=smoke_plan,
            source_plan_path=plan,
        )
        path = write_live_smoke_report(report, overwrite=overwrite)
    except (FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(str(path))


@app.command("live-audit-pipeline")
def live_audit_pipeline(
    run_id: Annotated[str, typer.Option("--run-id", help="Run identifier for audit artifacts.")],
    preflight_report: Annotated[
        Path,
        typer.Option("--preflight-report", help="JSON report from live-preflight."),
    ],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Pipeline mode: official_screen_only, debug_visible_bridge, or dry_run.",
        ),
    ],
    runs_dir: Annotated[
        Path,
        typer.Option("--runs-dir", help="Directory where future run logs will be stored."),
    ] = DEFAULT_RUNS_DIR,
    screenshots_dir: Annotated[
        Path,
        typer.Option(
            "--screenshots-dir",
            help="Directory where future screenshots will be stored.",
        ),
    ] = DEFAULT_SCREENSHOTS_DIR,
    reports_dir: Annotated[
        Path | None,
        typer.Option("--reports-dir", help="Directory where audit artifacts will be stored."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace existing audit artifact files."),
    ] = False,
) -> None:
    """Run the JSON-only live audit artifact pipeline."""
    allowed_modes = {"official_screen_only", "debug_visible_bridge", "dry_run"}
    if mode not in allowed_modes:
        msg = f"mode must be one of: {', '.join(sorted(allowed_modes))}"
        raise typer.BadParameter(msg)

    result = run_live_audit_pipeline(
        run_id=run_id,
        preflight_report_path=preflight_report,
        mode=mode,  # type: ignore[arg-type]
        runs_dir=runs_dir,
        screenshots_dir=screenshots_dir,
        reports_dir=reports_dir,
        overwrite=overwrite,
    )
    try:
        path = write_live_audit_pipeline_result(result, overwrite=overwrite)
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc
    if any(stage.status == "failed" for stage in result.stages):
        raise click.ClickException(f"live audit pipeline failed; summary written to {path}")
    typer.echo(str(path))


@app.command("controlled-live-smoke")
def controlled_live_smoke(
    pipeline_summary: Annotated[
        Path,
        typer.Option("--pipeline-summary", help="Live audit pipeline summary JSON path."),
    ],
    user_started: Annotated[
        bool,
        typer.Option("--user-started", help="Required explicit user-start gate."),
    ] = False,
    allow_real_runtime: Annotated[
        bool,
        typer.Option("--allow-real-runtime", help="Allow real runtime adapters if configured."),
    ] = False,
    allow_real_input: Annotated[
        bool,
        typer.Option("--allow-real-input", help="Keep false for observation-only smoke runs."),
    ] = False,
    target_window_title: Annotated[
        str | None,
        typer.Option("--target-window-title", help="Expected focused target window title."),
    ] = None,
    stop_file: Annotated[
        Path | None,
        typer.Option("--stop-file", help="Stop-file path for emergency stop."),
    ] = None,
    output_run_dir: Annotated[
        Path | None,
        typer.Option(
            "--run-dir",
            "--output-run-dir",
            help="Run directory for controlled smoke outputs.",
        ),
    ] = None,
    capture_command: Annotated[
        str | None,
        typer.Option(
            "--capture-command",
            help="Command that emits one binary PPM screenshot to stdout.",
        ),
    ] = None,
    max_frames: Annotated[
        int,
        typer.Option("--max-frames", min=1, max=30, help="Maximum frames to capture."),
    ] = 1,
    action_logging_mode: Annotated[
        str,
        typer.Option(
            "--action-logging-mode",
            help="Action intent logging mode: disabled or wait_only_noop.",
        ),
    ] = "disabled",
    dryrun_orchestration: Annotated[
        str,
        typer.Option(
            "--dryrun-orchestration",
            help="Dry-run task/skill orchestration mode: disabled or wait_only.",
        ),
    ] = "disabled",
    real_input_mode: Annotated[
        str,
        typer.Option(
            "--real-input-mode",
            help="Real input mode: disabled, wait_only_noop, or single_directional_tap.",
        ),
    ] = "disabled",
    allowed_real_primitive: Annotated[
        str | None,
        typer.Option(
            "--allowed-real-primitive",
            help="Allowed primitive for single_directional_tap; only move_right_short is accepted.",
        ),
    ] = None,
    max_input_count: Annotated[
        int,
        typer.Option(
            "--max-input-count",
            min=0,
            help="Maximum real inputs allowed; must be 1 for single_directional_tap.",
        ),
    ] = 0,
    input_rate_limit_seconds: Annotated[
        float,
        typer.Option(
            "--input-rate-limit-seconds",
            min=0.0,
            help="Minimum seconds between real wait/no-op inputs.",
        ),
    ] = 0.0,
    noop_action_frequency: Annotated[
        int,
        typer.Option(
            "--noop-action-frequency",
            min=1,
            help="Log one wait intent every N captured frames in wait_only_noop mode.",
        ),
    ] = 1,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing controlled smoke report."),
    ] = False,
) -> None:
    """Run an observation-only smoke capture when all explicit safety gates pass."""
    if not user_started:
        raise click.ClickException("controlled-live-smoke requires --user-started")
    if not allow_real_runtime:
        raise click.ClickException(
            "controlled-live-smoke did not start: --allow-real-runtime was not provided"
        )
    if action_logging_mode not in {"disabled", "wait_only_noop"}:
        raise click.ClickException("--action-logging-mode must be disabled or wait_only_noop")
    if dryrun_orchestration not in {"disabled", "wait_only"}:
        raise click.ClickException("--dryrun-orchestration must be disabled or wait_only")
    if real_input_mode not in {"disabled", "wait_only_noop", "single_directional_tap"}:
        raise click.ClickException(
            "--real-input-mode must be disabled, wait_only_noop, or single_directional_tap"
        )
    if dryrun_orchestration == "wait_only" and action_logging_mode != "disabled":
        raise click.ClickException(
            "--dryrun-orchestration wait_only cannot be combined with wait_only_noop logging"
        )
    if real_input_mode == "wait_only_noop":
        if not allow_real_input:
            raise click.ClickException(
                "--real-input-mode wait_only_noop requires --allow-real-input"
            )
        if action_logging_mode != "disabled" or dryrun_orchestration != "disabled":
            raise click.ClickException(
                "--real-input-mode wait_only_noop cannot be combined with logging or dry-run"
            )
        if max_input_count < 1:
            raise click.ClickException(
                "--real-input-mode wait_only_noop requires --max-input-count >= 1"
            )
        if not capture_command or "capture_active_window_ppm.sh" not in capture_command:
            raise click.ClickException(
                "--real-input-mode wait_only_noop requires scripts/capture_active_window_ppm.sh"
            )
    elif real_input_mode == "single_directional_tap":
        if not allow_real_input:
            raise click.ClickException(
                "--real-input-mode single_directional_tap requires --allow-real-input"
            )
        if action_logging_mode != "disabled" or dryrun_orchestration != "disabled":
            raise click.ClickException(
                "--real-input-mode single_directional_tap cannot be combined with "
                "logging or dry-run"
            )
        if allowed_real_primitive != "move_right_short":
            raise click.ClickException(
                "--real-input-mode single_directional_tap requires "
                "--allowed-real-primitive move_right_short"
            )
        if max_input_count != 1:
            raise click.ClickException(
                "--real-input-mode single_directional_tap requires --max-input-count 1"
            )
        if max_frames < 2:
            raise click.ClickException(
                "--real-input-mode single_directional_tap requires --max-frames at least 2"
            )
        if not capture_command or capture_command != "./scripts/capture_active_window_ppm.sh":
            raise click.ClickException(
                "--real-input-mode single_directional_tap requires "
                "--capture-command ./scripts/capture_active_window_ppm.sh"
            )
    elif allow_real_input:
        raise click.ClickException("--allow-real-input requires an explicit --real-input-mode")
    if capture_command and "capture_one_frame_ppm.sh" in capture_command:
        raise click.ClickException(
            "controlled-live-smoke requires scripts/capture_active_window_ppm.sh"
        )
    if target_window_title is None:
        raise click.ClickException("--target-window-title is required with --allow-real-runtime")
    try:
        pipeline = read_live_audit_pipeline_result(pipeline_summary)
        run_id = output_run_dir.name if output_run_dir is not None else pipeline.run_id
        resolved_stop_file = stop_file or (
            output_run_dir / "STOP" if output_run_dir is not None else None
        )
        screenshots_dir = output_run_dir / "screenshots" if output_run_dir is not None else None
        bundle = build_controlled_runtime_adapters(
            allow_real_runtime=allow_real_runtime,
            allow_real_input=allow_real_input,
            run_id=run_id,
            target_window_title=target_window_title,
            stop_file_path=resolved_stop_file,
            screenshots_dir=screenshots_dir,
            capture_command=capture_command,
        )
        result = run_controlled_live_smoke(
            user_started=user_started,
            pipeline_summary_path=pipeline_summary,
            focus_check=bundle.focus_check,
            emergency_stop_available=bundle.emergency_stop_available,
            emergency_stop_triggered=bundle.emergency_stop_triggered,
            capture_frame=bundle.capture_frame,
            log_event=lambda event: None,
            allow_real_input=allow_real_input,
            max_frames=max_frames,
            output_run_dir=output_run_dir,
            action_logging_mode=action_logging_mode,  # type: ignore[arg-type]
            dryrun_orchestration_mode=dryrun_orchestration,  # type: ignore[arg-type]
            real_input_mode=real_input_mode,  # type: ignore[arg-type]
            send_wait_noop=_send_wait_noop if real_input_mode == "wait_only_noop" else None,
            send_real_primitive=(
                _send_single_directional_tap
                if real_input_mode == "single_directional_tap"
                else None
            ),
            allowed_real_primitives=(
                (allowed_real_primitive,) if allowed_real_primitive is not None else ()
            ),
            max_input_count=max_input_count,
            input_rate_limit_seconds=input_rate_limit_seconds,
            capture_script=capture_command,
            noop_action_frequency=noop_action_frequency,
            overwrite=overwrite,
        )
    except (FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(result.report_path))


def _send_wait_noop() -> bool:
    return True


def _send_single_directional_tap(action: str) -> bool:
    if action != "move_right_short":
        return False
    completed = run(
        ["xdotool", "key", "--clearmodifiers", "Right"],
        capture_output=True,
        check=False,
        timeout=1.0,
    )
    return completed.returncode == 0


@app.command("controlled-live-smoke-validate")
def controlled_live_smoke_validate(
    report: Annotated[
        Path,
        typer.Option("--report", help="Controlled live-smoke report JSON path."),
    ],
    expected_frame_count: Annotated[
        int | None,
        typer.Option("--expected-frame-count", min=0, help="Expected captured frame count."),
    ] = 1,
    min_frame_count: Annotated[
        int | None,
        typer.Option("--min-frame-count", min=0, help="Minimum captured frame count."),
    ] = None,
    max_frame_count: Annotated[
        int | None,
        typer.Option("--max-frame-count", min=0, help="Maximum captured frame count."),
    ] = None,
    events_jsonl: Annotated[
        Path | None,
        typer.Option("--events-jsonl", help="Optional runtime events JSONL artifact."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Validation report output path."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing validation report."),
    ] = False,
) -> None:
    """Validate one-frame controlled live-smoke artifacts without runtime access."""
    validation = validate_controlled_live_smoke_artifacts(
        report_path=report,
        expected_frame_count=expected_frame_count,
        min_frame_count=min_frame_count,
        max_frame_count=max_frame_count,
        events_jsonl_path=events_jsonl,
    )
    output_path = output or default_validation_report_path(report)
    try:
        path = write_controlled_live_smoke_validation_report(
            validation,
            output_path,
            overwrite=overwrite,
        )
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc
    if not validation.status.passed:
        raise click.ClickException(f"controlled live-smoke validation failed: {path}")
    typer.echo(str(path))


@app.command("controlled-live-smoke-review")
def controlled_live_smoke_review(
    run_dir: Annotated[
        Path,
        typer.Option("--run-dir", help="Controlled live-smoke run directory."),
    ],
    min_frame_count: Annotated[
        int | None,
        typer.Option("--min-frame-count", min=0, help="Minimum accepted frame count."),
    ] = None,
    max_frame_count: Annotated[
        int | None,
        typer.Option("--max-frame-count", min=0, help="Maximum accepted frame count."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing review summary."),
    ] = False,
) -> None:
    """Write a review summary for existing controlled live-smoke artifacts."""
    try:
        summary = create_controlled_live_smoke_review_summary(
            run_dir=run_dir,
            min_frame_count=min_frame_count,
            max_frame_count=max_frame_count,
        )
        path = write_controlled_live_smoke_review_summary(
            summary,
            overwrite=overwrite,
        )
    except (FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(path))


@app.command("controlled-live-smoke-record-manual-review")
def controlled_live_smoke_record_manual_review(
    review: Annotated[
        Path,
        typer.Option("--review", help="Controlled live-smoke review JSON path."),
    ],
    status: Annotated[
        str,
        typer.Option("--status", help="Manual visual review status: passed or failed."),
    ],
    notes: Annotated[
        str | None,
        typer.Option("--notes", help="Optional human visual review notes."),
    ] = None,
    reviewer: Annotated[
        str | None,
        typer.Option("--reviewer", help="Optional human reviewer identifier."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Output review JSON path."),
    ] = None,
    in_place: Annotated[
        bool,
        typer.Option("--in-place", help="Update the review JSON in place."),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing output review JSON."),
    ] = False,
) -> None:
    """Record a human manual visual review result in an existing review JSON."""
    if status not in {"passed", "failed"}:
        raise typer.BadParameter("--status must be passed or failed")
    if output is not None and in_place:
        raise click.ClickException("--output and --in-place are mutually exclusive")
    if output is None and not in_place:
        raise click.ClickException("provide --output or --in-place")
    destination = review if in_place else output
    if destination is None:
        raise click.ClickException("provide --output or --in-place")
    try:
        status_value = cast(Literal["passed", "failed"], status)
        payload = record_controlled_live_smoke_manual_visual_review(
            review_path=review,
            status=status_value,
            notes=notes,
            reviewer=reviewer,
        )
        path = write_controlled_live_smoke_manual_visual_review(
            payload,
            destination,
            overwrite=overwrite or in_place,
        )
    except (FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(path))


@app.command("controlled-live-smoke-stability-review")
def controlled_live_smoke_stability_review(
    report: Annotated[
        list[Path],
        typer.Option(
            "--report",
            help="Controlled live-smoke report JSON path. Repeat once per run.",
        ),
    ],
    validation: Annotated[
        list[Path],
        typer.Option(
            "--validation",
            help="Controlled live-smoke validator JSON path. Repeat once per run.",
        ),
    ],
    review: Annotated[
        list[Path],
        typer.Option(
            "--review",
            help="Controlled live-smoke mechanical/manual review JSON path. Repeat once per run.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", help="Stability review output JSON path."),
    ] = Path("runs/controlled_live_smoke_stability_review.json"),
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing stability review."),
    ] = False,
) -> None:
    """Aggregate three manual single directional tap stability reviews."""
    try:
        summary = create_controlled_live_smoke_stability_review(
            report_paths=tuple(report),
            validation_paths=tuple(validation),
            review_paths=tuple(review),
        )
        path = write_controlled_live_smoke_stability_review(
            summary,
            output,
            overwrite=overwrite,
        )
    except (FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if summary.conclusion != "passed":
        raise click.ClickException(f"controlled live-smoke stability review failed: {path}")
    typer.echo(str(path))


def _parse_spatial_sequence_source(value: str) -> SpatialCorpusSequenceSource:
    parts = value.split(":", maxsplit=2)
    if len(parts) != 3 or not all(parts):
        msg = "--sequence must use SEQUENCE_ID:RELATIVE_DIRECTORY:SPLIT"
        raise ValueError(msg)
    sequence_id, relative_directory, split = parts
    return SpatialCorpusSequenceSource(
        sequence_id=sequence_id,
        relative_directory=relative_directory,
        split=split,
    )


def _parse_spatial_coordinate(value: str) -> tuple[int, int]:
    parts = value.split(",")
    if len(parts) != 2:
        msg = "coordinates must use X,Y"
        raise ValueError(msg)
    try:
        return int(parts[0]), int(parts[1])
    except ValueError as exc:
        msg = "coordinates must use integer X,Y values"
        raise ValueError(msg) from exc


def _read_spatial_annotation_workflow(path: Path) -> SpatialAnnotationWorkflow:
    try:
        return SpatialAnnotationWorkflow.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        msg = f"invalid spatial annotation workflow: {path}: {exc}"
        raise ValueError(msg) from exc


def _write_spatial_annotation_workflow(
    workflow: SpatialAnnotationWorkflow,
    path: Path,
    *,
    overwrite: bool,
) -> Path:
    if path.exists() and not overwrite:
        msg = f"workflow output already exists: {path}"
        raise FileExistsError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_to_deterministic_json(workflow) + "\n", encoding="utf-8")
    return path


def _spatial_annotation_by_frame_id(
    workflow: SpatialAnnotationWorkflow,
    frame_id: str,
) -> SpatialPerceptionFrameAnnotation:
    for sequence in workflow.manifest.annotations.sequences:
        for annotation in sequence.frames:
            if annotation.frame_id == frame_id:
                return annotation
    msg = f"annotation frame_id is not present in the corpus: {frame_id}"
    raise ValueError(msg)


def _to_deterministic_json(model: BaseModel) -> str:
    payload = model.model_dump(mode="json")  # type: ignore[union-attr]
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)


def main() -> None:
    app()
