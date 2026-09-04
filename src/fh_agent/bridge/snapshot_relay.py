"""One-shot relay of correlated snapshot responses into the local JSONL bridge feed."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from fh_agent.bridge.snapshot_request import BridgeSnapshotRequest
from fh_agent.bridge.snapshot_response import (
    BridgeSnapshotResponse,
    BridgeSnapshotResponseError,
    unwrap_bridge_snapshot_response,
)


class BridgeSnapshotRelayError(ValueError):
    """Raised when a snapshot response cannot be relayed safely."""


def _reject_nonfinite_json_constant(constant: str) -> None:
    msg = f"bridge snapshot response contains invalid JSON constant: {constant}"
    raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class BridgeSnapshotRelayResult:
    """Audit metadata for one response record appended to the local bridge feed."""

    request_id: str
    run_id: str
    screenshot_id: str
    response_path: Path
    feed_path: Path


def _read_snapshot_response(response_path: Path) -> BridgeSnapshotResponse:
    try:
        raw_response = response_path.read_bytes()
    except OSError as error:
        msg = "could not read bridge snapshot response"
        raise BridgeSnapshotRelayError(msg) from error

    if not raw_response.endswith(b"\n"):
        msg = "bridge snapshot response is incomplete"
        raise BridgeSnapshotRelayError(msg)

    try:
        decoded_response = raw_response.decode("utf-8")
    except UnicodeDecodeError as error:
        msg = "bridge snapshot response is not valid UTF-8"
        raise BridgeSnapshotRelayError(msg) from error

    try:
        response_data = json.loads(
            decoded_response,
            parse_constant=_reject_nonfinite_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as error:
        msg = "bridge snapshot response is not valid JSON"
        raise BridgeSnapshotRelayError(msg) from error

    if not isinstance(response_data, dict):
        msg = "bridge snapshot response root must be an object"
        raise BridgeSnapshotRelayError(msg)

    try:
        return BridgeSnapshotResponse.model_validate(response_data)
    except ValidationError as error:
        msg = "bridge snapshot response envelope is invalid"
        raise BridgeSnapshotRelayError(msg) from error


def relay_bridge_snapshot_response(
    request: BridgeSnapshotRequest,
    *,
    response_path: Path,
    feed_path: Path,
) -> BridgeSnapshotRelayResult:
    """Correlate one complete response, then append its unchanged raw payload as JSONL."""

    response = _read_snapshot_response(response_path)
    try:
        raw_payload = unwrap_bridge_snapshot_response(response, request)
    except BridgeSnapshotResponseError as error:
        msg = "bridge snapshot response does not match request"
        raise BridgeSnapshotRelayError(msg) from error

    try:
        record = (
            json.dumps(
                raw_payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as error:
        msg = "bridge snapshot payload is not JSON serializable"
        raise BridgeSnapshotRelayError(msg) from error

    try:
        with feed_path.open("ab") as file:
            file.write(record)
            file.flush()
            os.fsync(file.fileno())
    except OSError as error:
        msg = "could not append bridge snapshot payload to feed"
        raise BridgeSnapshotRelayError(msg) from error

    return BridgeSnapshotRelayResult(
        request_id=request.request_id,
        run_id=request.run_id,
        screenshot_id=request.screenshot_id,
        response_path=response_path,
        feed_path=feed_path,
    )
