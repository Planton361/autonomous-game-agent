from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fh_agent.cli import app
from fh_agent.memory.event_log import EventLogger
from fh_agent.perception.capture_session import CaptureSession, CaptureSessionConfig
from fh_agent.perception.screen_capture import DummyScreenCapture


class ManualClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


def make_session(tmp_path: Path, *, frame_count: int = 3) -> CaptureSession:
    return CaptureSession(
        CaptureSessionConfig(
            run_id="run-1",
            frame_count=frame_count,
            screenshots_dir=tmp_path / "screenshots",
            runs_dir=tmp_path / "runs",
        ),
        capture=DummyScreenCapture(clock=ManualClock()),
    )


def test_capture_session_saves_requested_number_of_frames(tmp_path: Path) -> None:
    session = make_session(tmp_path, frame_count=3)

    result = session.run()

    assert result.frames_saved == 3
    assert result.screenshot_dir == tmp_path / "screenshots" / "run-1"
    for evidence in result.evidence_records:
        assert evidence.kind == "screenshot"
        assert evidence.run_id == "run-1"
        assert Path(evidence.path).is_file()


def test_capture_session_logs_events_with_evidence_ids(tmp_path: Path) -> None:
    session = make_session(tmp_path, frame_count=2)

    result = session.run()
    records = EventLogger(result.event_log_path, run_id="run-1").read_all()

    assert records == result.event_records
    assert len(records) == 2
    for evidence, event in zip(result.evidence_records, records, strict=True):
        assert event.event_type == "evidence"
        assert event.evidence_ids == [evidence.evidence_id]
        assert event.payload["kind"] == "screenshot"
        assert event.payload["sha256"] == evidence.sha256


def test_capture_session_does_not_overwrite_existing_run_without_explicit_permission(
    tmp_path: Path,
) -> None:
    session = make_session(tmp_path, frame_count=1)
    session.run()

    with pytest.raises(FileExistsError):
        make_session(tmp_path, frame_count=1).run()


def test_cli_help_still_works() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "capture" in result.output


def test_cli_capture_uses_dummy_backend(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "capture",
            "--frames",
            "2",
            "--run-id",
            "cli-run",
            "--screenshots-dir",
            str(tmp_path / "screenshots"),
            "--runs-dir",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code == 0
    assert "run_id: cli-run" in result.output
    assert "frames_saved: 2" in result.output
    assert (tmp_path / "runs" / "cli-run" / "events.jsonl").is_file()
    assert len(list((tmp_path / "screenshots" / "cli-run").glob("*.ppm"))) == 2
