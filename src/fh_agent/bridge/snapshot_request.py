"""Screenshot-bound requests for future bridge-visible-state snapshots."""

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.bridge.evidence_sync import BridgeScreenshotEvidenceLookup


class BridgeSnapshotRequestError(ValueError):
    """Raised when a bridge snapshot request cannot be safely created or published."""


class BridgeSnapshotRequest(BaseModel):
    """One bridge-assisted snapshot request bound to durable screenshot evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    run_mode: Literal["bridge-assisted"] = "bridge-assisted"
    screenshot_id: str = Field(min_length=1)

    @field_validator("request_id", "run_id", "screenshot_id")
    @classmethod
    def id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            msg = "snapshot request IDs must not be blank"
            raise ValueError(msg)
        return value


def create_bridge_snapshot_request(
    *,
    request_id: str,
    run_id: str,
    screenshot_id: str,
    screenshot_evidence_lookup: BridgeScreenshotEvidenceLookup,
) -> BridgeSnapshotRequest:
    """Create a request only for the latest durable screenshot of its run."""

    request = BridgeSnapshotRequest(
        request_id=request_id,
        run_id=run_id,
        screenshot_id=screenshot_id,
    )
    latest_screenshot_evidence_id = screenshot_evidence_lookup.latest_screenshot_evidence_id(
        run_id=request.run_id
    )
    if latest_screenshot_evidence_id is None:
        msg = "no durable screenshot evidence exists for bridge snapshot request"
        raise BridgeSnapshotRequestError(msg)
    if latest_screenshot_evidence_id != request.screenshot_id:
        msg = "snapshot request screenshot_id does not match latest durable screenshot evidence"
        raise BridgeSnapshotRequestError(msg)

    return request


def write_bridge_snapshot_request(request: BridgeSnapshotRequest, path: Path) -> Path:
    """Atomically publish one request without overwriting an existing target."""

    if path.exists():
        msg = f"bridge snapshot request target already exists: {path}"
        raise BridgeSnapshotRequestError(msg)

    payload = json.dumps(
        request.model_dump(mode="json"),
        separators=(",", ":"),
        sort_keys=True,
    )
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
    except OSError as error:
        msg = "could not create temporary bridge snapshot request"
        raise BridgeSnapshotRequestError(msg) from error

    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(payload)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        # A same-directory hard link publishes the completed temp file atomically and
        # fails rather than replacing a concurrent existing target.
        os.link(temporary_path, path)
    except FileExistsError as error:
        msg = f"bridge snapshot request target already exists: {path}"
        raise BridgeSnapshotRequestError(msg) from error
    except OSError as error:
        msg = "could not publish bridge snapshot request"
        raise BridgeSnapshotRequestError(msg) from error
    finally:
        temporary_path.unlink(missing_ok=True)

    return path
