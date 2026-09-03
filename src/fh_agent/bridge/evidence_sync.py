"""Read-only screenshot-evidence lookup for the bridge-assisted boundary."""

from pathlib import Path
from typing import Protocol

from fh_agent.memory.event_log import EventLogger


class BridgeScreenshotEvidenceLookup(Protocol):
    """Looks up the latest durable screenshot evidence for one run."""

    def latest_screenshot_evidence_id(self, *, run_id: str) -> str | None:
        """Return the latest durable screenshot evidence ID for the run."""


class BridgeEvidenceSynchronizationError(ValueError):
    """Raised when a bridge-assisted payload lacks current screenshot evidence."""


class EventLogBridgeScreenshotEvidenceLookup:
    """Read the latest valid screenshot evidence ID from an append-only event log."""

    def __init__(self, event_log_path: Path) -> None:
        self._event_log_path = event_log_path

    def latest_screenshot_evidence_id(self, *, run_id: str) -> str | None:
        """Return the latest valid screenshot evidence ID recorded for ``run_id``."""

        latest_screenshot_evidence_id: str | None = None
        records = EventLogger(self._event_log_path, run_id=run_id).read_all()
        for record in records:
            if record.run_id != run_id or record.event_type != "evidence":
                continue
            if record.payload.get("kind") != "screenshot":
                continue
            if len(record.evidence_ids) != 1 or not record.evidence_ids[0]:
                continue
            latest_screenshot_evidence_id = record.evidence_ids[0]

        return latest_screenshot_evidence_id
