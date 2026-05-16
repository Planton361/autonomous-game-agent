from dataclasses import dataclass
from pathlib import Path

from fh_agent.memory.event_log import EventLogger, EventRecord
from fh_agent.memory.evidence import EvidenceRecord, EvidenceStore
from fh_agent.perception.screen_capture import ScreenCapture


@dataclass(frozen=True, slots=True)
class CaptureSessionConfig:
    run_id: str
    frame_count: int
    screenshots_dir: Path
    runs_dir: Path
    allow_existing_run: bool = False


@dataclass(frozen=True, slots=True)
class CaptureSessionResult:
    run_id: str
    evidence_records: list[EvidenceRecord]
    event_records: list[EventRecord]
    event_log_path: Path
    screenshot_dir: Path

    @property
    def frames_saved(self) -> int:
        return len(self.evidence_records)


class CaptureSession:
    """Coordinates raw capture, screenshot evidence, and JSONL event logging."""

    def __init__(
        self,
        config: CaptureSessionConfig,
        capture: ScreenCapture,
        *,
        evidence_store: EvidenceStore | None = None,
        event_logger: EventLogger | None = None,
    ) -> None:
        if not config.run_id:
            msg = "run_id must not be empty"
            raise ValueError(msg)
        if config.frame_count < 0:
            msg = "frame_count must be non-negative"
            raise ValueError(msg)

        self.config = config
        self.capture = capture
        self.screenshot_dir = config.screenshots_dir / config.run_id
        self.event_log_path = config.runs_dir / config.run_id / "events.jsonl"
        self.evidence_store = evidence_store or EvidenceStore(
            config.screenshots_dir,
            run_id=config.run_id,
        )
        self.event_logger = event_logger or EventLogger(
            self.event_log_path,
            run_id=config.run_id,
        )

    def run(self) -> CaptureSessionResult:
        self._ensure_run_is_writable()

        evidence_records: list[EvidenceRecord] = []
        event_records: list[EventRecord] = []
        for frame_index in range(self.config.frame_count):
            frame = self.capture.capture()
            evidence = self.evidence_store.save_screenshot(frame)
            event = self.event_logger.append(
                "evidence",
                payload={
                    "kind": evidence.kind,
                    "frame_index": frame_index,
                    "path": evidence.path,
                    "sha256": evidence.sha256,
                    "width": evidence.width,
                    "height": evidence.height,
                },
                evidence_ids=[evidence.evidence_id],
            )
            evidence_records.append(evidence)
            event_records.append(event)

        return CaptureSessionResult(
            run_id=self.config.run_id,
            evidence_records=evidence_records,
            event_records=event_records,
            event_log_path=self.event_log_path,
            screenshot_dir=self.screenshot_dir,
        )

    def _ensure_run_is_writable(self) -> None:
        if self.config.allow_existing_run:
            return

        if self.screenshot_dir.exists() or self.event_log_path.exists():
            msg = f"run already exists: {self.config.run_id}"
            raise FileExistsError(msg)
