from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from shlex import split
from subprocess import run
from typing import Protocol
from uuid import uuid4

from fh_agent.evals.controlled_live_smoke_runner import ControlledLiveSmokeFrame


class FrameCaptureBackend(Protocol):
    def capture(self): ...


class EvidenceStoreBackend(Protocol):
    def save_screenshot(self, frame) -> "EvidenceRecordLike": ...


class EvidenceRecordLike(Protocol):
    evidence_id: str
    path: str
    created_at: datetime
    width: int
    height: int
    sha256: str


class FocusCheckAdapter:
    """Checks whether the configured visible target appears focused."""

    def __init__(
        self,
        *,
        target_title: str,
        window_title_probe: Callable[[], str | None] | None = None,
        focused_probe: Callable[[], bool] | None = None,
        exact_title_match: bool = False,
    ) -> None:
        self.target_title = target_title
        self.window_title_probe = window_title_probe
        self.focused_probe = focused_probe
        self.exact_title_match = exact_title_match

    def __call__(self) -> bool:
        if self.focused_probe is not None:
            return self.focused_probe()
        if self.window_title_probe is None:
            return False
        active_title = self.window_title_probe()
        if active_title is None:
            return False
        if self.exact_title_match:
            return active_title == self.target_title
        return self.target_title in active_title


class ActiveWindowTitleProbe:
    """Best-effort active-window title probe; returns None when unavailable."""

    def __call__(self) -> str | None:
        try:
            active = run(
                ["xdotool", "getactivewindow"],
                capture_output=True,
                check=False,
                timeout=1.0,
            )
            if active.returncode != 0:
                return None
            window_id = active.stdout.decode("utf-8", errors="ignore").strip()
            if not window_id:
                return None
            title = run(
                ["xdotool", "getwindowname", window_id],
                capture_output=True,
                check=False,
                timeout=1.0,
            )
            if title.returncode != 0:
                return None
            return title.stdout.decode("utf-8", errors="ignore").strip()
        except OSError:
            return None


@dataclass(frozen=True, slots=True)
class CapturedPpmFrame:
    width: int
    height: int
    ppm_bytes: bytes
    captured_at: datetime

    def to_ppm_bytes(self) -> bytes:
        return self.ppm_bytes


class SubprocessPpmCaptureBackend:
    """Runs an explicit user-configured command that emits one binary PPM frame."""

    def __init__(
        self,
        command: tuple[str, ...],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not command:
            msg = "capture command must not be empty"
            raise ValueError(msg)
        self.command = command
        self.clock = clock or (lambda: datetime.now(UTC))

    @classmethod
    def from_command_string(
        cls,
        command: str,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> "SubprocessPpmCaptureBackend":
        return cls(tuple(split(command)), clock=clock)

    def capture(self) -> CapturedPpmFrame:
        completed = run(
            list(self.command),
            capture_output=True,
            check=False,
            timeout=5.0,
        )
        if completed.returncode != 0:
            msg = "capture command failed"
            raise RuntimeError(msg)
        width, height = _ppm_dimensions(completed.stdout)
        return CapturedPpmFrame(
            width=width,
            height=height,
            ppm_bytes=completed.stdout,
            captured_at=self.clock(),
        )


class StopFileEmergencyStopAdapter:
    """Stop-file emergency adapter: file exists means stop immediately."""

    def __init__(self, stop_file_path: Path) -> None:
        self.stop_file_path = stop_file_path

    def is_available(self) -> bool:
        try:
            self.stop_file_path.parent.mkdir(parents=True, exist_ok=True)
            probe = self.stop_file_path.parent / ".emergency_stop_probe"
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink()
        except OSError:
            return False
        return True

    def is_triggered(self) -> bool:
        return self.stop_file_path.exists()

    def __call__(self) -> bool:
        return self.is_triggered()


class OneFrameCaptureAdapter:
    """Captures one visible frame through an injected backend and stores evidence."""

    def __init__(
        self,
        *,
        capture_backend: FrameCaptureBackend,
        evidence_store: EvidenceStoreBackend,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.capture_backend = capture_backend
        self.evidence_store = evidence_store
        self.clock = clock or (lambda: datetime.now(UTC))

    def __call__(self) -> ControlledLiveSmokeFrame:
        frame = self.capture_backend.capture()
        record = self.evidence_store.save_screenshot(frame)
        return ControlledLiveSmokeFrame(
            evidence_id=record.evidence_id,
            screenshot_path=Path(record.path),
            timestamp=record.created_at,
            width=record.width,
            height=record.height,
            sha256=record.sha256,
        )


@dataclass(frozen=True, slots=True)
class ControlledRuntimeAdapterBundle:
    focus_check: Callable[[], bool]
    emergency_stop_available: Callable[[], bool]
    emergency_stop_triggered: Callable[[], bool]
    capture_frame: Callable[[], ControlledLiveSmokeFrame]
    stop_file_path: Path


def build_controlled_runtime_adapters(
    *,
    allow_real_runtime: bool,
    allow_real_input: bool = False,
    run_id: str,
    target_window_title: str,
    stop_file_path: Path | None = None,
    screenshots_dir: Path | None = None,
    window_title_probe: Callable[[], str | None] | None = None,
    focused_probe: Callable[[], bool] | None = None,
    capture_backend: FrameCaptureBackend | None = None,
    capture_command: str | None = None,
    evidence_store: EvidenceStoreBackend | None = None,
) -> ControlledRuntimeAdapterBundle:
    """Build observation-only runtime adapters without sending input."""

    if not allow_real_runtime:
        msg = "controlled runtime adapters require allow_real_runtime=True"
        raise ValueError(msg)
    if allow_real_input:
        msg = "real input is refused for controlled live smoke 12.7"
        raise ValueError(msg)
    if not target_window_title:
        msg = "target_window_title is required"
        raise ValueError(msg)
    if capture_backend is None and capture_command is None:
        msg = "capture_backend or capture_command is required for real screen capture"
        raise ValueError(msg)

    resolved_stop_file = stop_file_path or Path("runs") / run_id / "STOP"
    focus = FocusCheckAdapter(
        target_title=target_window_title,
        window_title_probe=window_title_probe or ActiveWindowTitleProbe(),
        focused_probe=focused_probe,
    )
    emergency = StopFileEmergencyStopAdapter(resolved_stop_file)
    store = evidence_store or _build_evidence_store(screenshots_dir=screenshots_dir, run_id=run_id)
    resolved_capture_backend = capture_backend or SubprocessPpmCaptureBackend.from_command_string(
        capture_command or ""
    )
    capture = OneFrameCaptureAdapter(
        capture_backend=resolved_capture_backend,
        evidence_store=store,
    )
    return ControlledRuntimeAdapterBundle(
        focus_check=focus,
        emergency_stop_available=emergency.is_available,
        emergency_stop_triggered=emergency.is_triggered,
        capture_frame=capture,
        stop_file_path=resolved_stop_file,
    )


def _build_evidence_store(
    *,
    screenshots_dir: Path | None,
    run_id: str,
) -> EvidenceStoreBackend:
    target_dir = screenshots_dir or Path("runs") / run_id / "screenshots"
    return _PpmEvidenceStore(target_dir)


@dataclass(frozen=True, slots=True)
class _PpmEvidenceRecord:
    evidence_id: str
    path: str
    created_at: datetime
    width: int
    height: int
    sha256: str


class _PpmEvidenceStore:
    def __init__(
        self,
        root: Path,
        *,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.root = root
        self.id_factory = id_factory or (lambda: uuid4().hex)

    def save_screenshot(self, frame) -> _PpmEvidenceRecord:
        evidence_id = self.id_factory()
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{evidence_id}.ppm"
        path.write_bytes(frame.to_ppm_bytes())
        return _PpmEvidenceRecord(
            evidence_id=evidence_id,
            path=str(path),
            created_at=frame.captured_at,
            width=frame.width,
            height=frame.height,
            sha256=sha256(path.read_bytes()).hexdigest(),
        )


def _ppm_dimensions(payload: bytes) -> tuple[int, int]:
    parts = payload.split(maxsplit=4)
    if len(parts) < 4 or parts[0] != b"P6":
        msg = "capture command must emit binary PPM P6 data"
        raise ValueError(msg)
    try:
        width = int(parts[1])
        height = int(parts[2])
        max_value = int(parts[3])
    except ValueError as exc:
        msg = "invalid PPM header from capture command"
        raise ValueError(msg) from exc
    if width <= 0 or height <= 0 or max_value != 255:
        msg = "unsupported PPM dimensions or max value"
        raise ValueError(msg)
    return width, height
