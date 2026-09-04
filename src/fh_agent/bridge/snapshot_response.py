"""Request-correlated raw responses from the visible bridge."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.bridge.snapshot_request import BridgeSnapshotRequest


class BridgeSnapshotResponseError(ValueError):
    """Raised when a bridge snapshot response cannot be correlated safely."""


class BridgeSnapshotResponse(BaseModel):
    """Raw visible bridge payload correlated to one snapshot request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    payload: dict[str, Any]

    @field_validator("request_id", "run_id")
    @classmethod
    def id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            msg = "snapshot response IDs must not be blank"
            raise ValueError(msg)
        return value


def unwrap_bridge_snapshot_response(
    response: BridgeSnapshotResponse,
    request: BridgeSnapshotRequest,
) -> Mapping[str, Any]:
    """Return a raw payload only when its response envelope matches its request exactly."""

    if response.request_id != request.request_id:
        msg = "snapshot response request_id does not match request"
        raise BridgeSnapshotResponseError(msg)
    if response.run_id != request.run_id:
        msg = "snapshot response run_id does not match request"
        raise BridgeSnapshotResponseError(msg)
    if response.payload.get("run_mode") != request.run_mode:
        msg = "snapshot response payload run_mode does not match request"
        raise BridgeSnapshotResponseError(msg)
    if response.payload.get("screenshot_id") != request.screenshot_id:
        msg = "snapshot response payload screenshot_id does not match request"
        raise BridgeSnapshotResponseError(msg)

    return response.payload
