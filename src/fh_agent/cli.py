from pathlib import Path
from typing import Annotated, cast

import click
import typer
from rich.console import Console

from fh_agent import __version__
from fh_agent.evals.controlled_live_runtime_adapters import build_controlled_runtime_adapters
from fh_agent.evals.controlled_live_smoke_review import (
    create_controlled_live_smoke_review_summary,
    write_controlled_live_smoke_review_summary,
)
from fh_agent.evals.controlled_live_smoke_runner import (
    read_live_audit_pipeline_result,
    run_controlled_live_smoke,
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
    capture_command: Annotated[
        str | None,
        typer.Option(
            "--capture-command",
            help="Command that emits one binary PPM screenshot to stdout.",
        ),
    ] = None,
    max_frames: Annotated[
        int,
        typer.Option("--max-frames", min=1, max=3, help="Maximum frames to capture."),
    ] = 1,
) -> None:
    """Run an observation-only smoke capture when all explicit safety gates pass."""
    if not user_started:
        raise click.ClickException("controlled-live-smoke requires --user-started")
    if not allow_real_runtime:
        raise click.ClickException(
            "controlled-live-smoke did not start: --allow-real-runtime was not provided"
        )
    if allow_real_input:
        raise click.ClickException(
            "controlled-live-smoke has no real input adapter in this skeleton"
        )
    if target_window_title is None:
        raise click.ClickException("--target-window-title is required with --allow-real-runtime")
    try:
        pipeline = read_live_audit_pipeline_result(pipeline_summary)
        bundle = build_controlled_runtime_adapters(
            allow_real_runtime=allow_real_runtime,
            allow_real_input=allow_real_input,
            run_id=pipeline.run_id,
            target_window_title=target_window_title,
            stop_file_path=stop_file,
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
            overwrite=True,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(result.report_path))


@app.command("controlled-live-smoke-validate")
def controlled_live_smoke_validate(
    report: Annotated[
        Path,
        typer.Option("--report", help="Controlled live-smoke report JSON path."),
    ],
    expected_frame_count: Annotated[
        int,
        typer.Option("--expected-frame-count", min=0, help="Expected captured frame count."),
    ] = 1,
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
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace an existing review summary."),
    ] = False,
) -> None:
    """Write a review summary for existing controlled live-smoke artifacts."""
    try:
        summary = create_controlled_live_smoke_review_summary(run_dir=run_dir)
        path = write_controlled_live_smoke_review_summary(
            summary,
            overwrite=overwrite,
        )
    except (FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(str(path))


def main() -> None:
    app()
