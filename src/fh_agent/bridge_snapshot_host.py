"""One-shot host composition from visible capture to a bridge snapshot request."""

from dataclasses import dataclass
from pathlib import Path

from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.snapshot_request import (
    BridgeSnapshotRequest,
    create_bridge_snapshot_request,
    write_bridge_snapshot_request,
)
from fh_agent.memory.event_log import EventLogger, EventRecord
from fh_agent.memory.evidence import EvidenceRecord, EvidenceStore
from fh_agent.perception.screen_capture import ScreenCapture


class BridgeSnapshotHostError(ValueError):
    """Raised when host capture composition cannot safely publish a request."""


@dataclass(frozen=True, slots=True)
class BridgeSnapshotHostResult:
    """Exact records created while binding one host capture to a bridge request."""

    evidence_record: EvidenceRecord
    evidence_event: EventRecord
    request: BridgeSnapshotRequest
    request_path: Path


def capture_and_publish_bridge_snapshot_request(
    capture: ScreenCapture,
    evidence_store: EvidenceStore,
    event_logger: EventLogger,
    *,
    run_id: str,
    request_id: str,
    request_path: Path,
) -> BridgeSnapshotHostResult:
    """Capture one frame, durably record it, then publish its screenshot-bound request."""

    if run_id != evidence_store.run_id or run_id != event_logger.run_id:
        msg = "bridge snapshot host run IDs must match before capture"
        raise BridgeSnapshotHostError(msg)
    if request_path.exists():
        msg = f"bridge snapshot request target already exists: {request_path}"
        raise BridgeSnapshotHostError(msg)

    evidence_record = evidence_store.save_screenshot(capture.capture())
    evidence_event = event_logger.append(
        "evidence",
        payload=evidence_record.model_dump(mode="json"),
        evidence_ids=[evidence_record.evidence_id],
    )
    request = create_bridge_snapshot_request(
        request_id=request_id,
        run_id=run_id,
        screenshot_id=evidence_record.evidence_id,
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_logger.path),
    )
    published_path = write_bridge_snapshot_request(request, request_path)

    return BridgeSnapshotHostResult(
        evidence_record=evidence_record,
        evidence_event=evidence_event,
        request=request,
        request_path=published_path,
    )
