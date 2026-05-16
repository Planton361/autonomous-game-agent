from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console

from fh_agent import __version__
from fh_agent.observation.schemas import UIState
from fh_agent.perception.capture_session import CaptureSession, CaptureSessionConfig
from fh_agent.perception.offline_processor import observation_to_json, process_saved_frame
from fh_agent.perception.screen_capture import DummyScreenCapture

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


def main() -> None:
    app()
